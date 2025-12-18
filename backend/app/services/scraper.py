from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import datetime
from pathlib import Path

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from app.config import settings
from app.exceptions import LinkedInScrapingError
from app.utils import validate_linkedin_profile_url

logger = logging.getLogger(__name__)


def _is_likely_linkedin_wall(html: str) -> tuple[bool, str | None]:
    """Best-effort detection of LinkedIn login/paywall/verification pages.

    We use HTML heuristics because analyzing screenshots would require OCR.
    These patterns are intentionally broad; we want to fail fast rather than
    feed a login wall into Gemini (which yields mostly-null outputs).

    Returns:
        (is_wall, reason)
    """
    if not html:
        return True, "Empty HTML returned"

    lowered = html.lower()

    # Common LinkedIn sign-in wall indicators.
    wall_patterns: list[tuple[str, str]] = [
        (r"sign\s*in\s+to\s+linkedin", "LinkedIn sign-in wall"),
        (r"join\s+linkedin", "LinkedIn join/sign-up wall"),
        (r"you\s+agree\s+to\s+the\s+linkedin\s+user\s+agreement", "LinkedIn auth page"),
        (r"authwall", "LinkedIn authwall"),
        (r"checkpoint/challenge", "LinkedIn verification checkpoint"),
        # NOTE: Do not treat generic "captcha" or "security verification" mentions
        # as a hard wall signal. LinkedIn pages often embed reCAPTCHA scripts even
        # when the user is logged in and viewing a normal profile.
        (r"unusual\s+activity", "LinkedIn unusual activity verification"),
        (r"verify\s+your\s+identity", "LinkedIn identity verification"),
        (r"restricted\s+access", "LinkedIn restricted access"),
    ]

    for pattern, reason in wall_patterns:
        if re.search(pattern, lowered):
            return True, reason

    # If the page doesn't appear to contain any typical profile content, treat it as suspect.
    # Profile pages usually contain at least one of these tokens.
    profile_hints = ["pv-top-card", "experience", "education", "about", "linkedin.com/in/"]
    if not any(hint in lowered for hint in profile_hints):
        return True, "Page does not look like a LinkedIn profile (likely blocked/login wall)"

    return False, None


class LinkedInScraper:
    """Scrape LinkedIn profile pages using Playwright.

    For MVP we only support a manual trigger flow (no scheduling).
    """

    def __init__(self) -> None:
        self._timeout_ms = int(settings.scraper_timeout_seconds * 1000)
        self._user_agent = settings.scraper_user_agent

        # Artifact dumping is optional and off by default.
        self._debug_artifacts = bool(settings.scraper_debug_artifacts)
        self._artifacts_dir = settings.scraper_artifacts_dir

        # Optional: reuse a logged-in session.
        self._storage_state_path = settings.linkedin_storage_state_path

        # LinkedIn often keeps connections open; networkidle can hang.
        self._goto_wait_until = "domcontentloaded"

        logger.info(
            "Scraper config: debug_artifacts=%s artifacts_dir=%s goto_wait_until=%s timeout_seconds=%s user_agent=%s",
            self._debug_artifacts,
            self._artifacts_dir,
            self._goto_wait_until,
            settings.scraper_timeout_seconds,
            (self._user_agent[:60] + "…") if self._user_agent and len(self._user_agent) > 60 else self._user_agent,
        )

        if self._storage_state_path:
            try:
                exists = Path(self._storage_state_path).expanduser().exists()
            except Exception:
                exists = False
            logger.info(
                "Scraper storage_state: configured=%s path=%s exists=%s",
                True,
                self._storage_state_path,
                exists,
            )
        else:
            logger.info("Scraper storage_state: configured=%s", False)

        # Best-effort preflight to surface the common "playwright install" issue.
        # We intentionally don't fail startup here because some environments install browsers later.
        # If it's missing, the first scrape attempt will still raise with a clear message.
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                # Launching briefly is the most reliable check that the executable exists.
                b = p.chromium.launch(headless=True)
                b.close()
        except Exception as e:
            logger.warning(
                "Playwright browser preflight failed. If you see 'Executable doesn't exist', run: python -m playwright install chromium",
                extra={"error": repr(e)},
            )

    def _maybe_dump_artifact(self, *, kind: str, url: str, data: bytes | str, suffix: str = "") -> None:
        if not self._debug_artifacts:
            return

        try:
            Path(self._artifacts_dir).mkdir(parents=True, exist_ok=True)
            ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
            safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", url)[:80]
            extra = f"_{suffix}" if suffix else ""
            if kind == "screenshot":
                path = os.path.join(self._artifacts_dir, f"{ts}_{safe}{extra}.png")
                with open(path, "wb") as f:
                    assert isinstance(data, (bytes, bytearray))
                    f.write(data)
            elif kind == "html":
                path = os.path.join(self._artifacts_dir, f"{ts}_{safe}{extra}.html")
                with open(path, "w", encoding="utf-8") as f:
                    assert isinstance(data, str)
                    f.write(data)
            else:
                return

            logger.info("Wrote scraper artifact", extra={"path": path, "kind": kind, "url": url})
        except Exception:
            logger.exception("Failed to write scraper artifact")

    async def screenshot_linkedin(self, url: str) -> bytes:
        """Capture a full-page PNG screenshot.

        Args:
            url: LinkedIn profile URL.

        Returns:
            PNG bytes.

        Raises:
            LinkedInScrapingError: On timeout or navigation failure.
        """
        normalized = validate_linkedin_profile_url(url)
        png, _html = await self._run_with_retry(lambda: self._scrape_once(normalized))
        self._maybe_dump_artifact(kind="screenshot", url=normalized, data=png)
        return png

    async def fetch_html(self, url: str) -> str:
        """Fetch the raw HTML of a LinkedIn profile page.

        Args:
            url: LinkedIn profile URL.

        Returns:
            HTML string.

        Raises:
            LinkedInScrapingError: On timeout or navigation failure.
        """
        normalized = validate_linkedin_profile_url(url)
        _png, html = await self._run_with_retry(lambda: self._scrape_once(normalized))
        self._maybe_dump_artifact(kind="html", url=normalized, data=html)
        is_wall, reason = _is_likely_linkedin_wall(html)
        if is_wall:
            hint = (
                "LinkedIn served a login/auth wall instead of the profile. "
                "For MVP, capture a logged-in session once and reuse it: "
                "python scripts/save_linkedin_storage_state.py --profile-url <profile>. "
                f"Artifacts saved under: {self._artifacts_dir}"
            )
            raise LinkedInScrapingError(f"LinkedIn blocked scraping ({reason}). {hint}")
        return html

    async def _run_with_retry(self, fn):
        try:
            return await asyncio.wait_for(fn(), timeout=settings.scraper_timeout_seconds)
        except TimeoutError:
            logger.warning("Scraper timeout, retrying once")
            try:
                return await asyncio.wait_for(fn(), timeout=settings.scraper_timeout_seconds)
            except TimeoutError as e:
                raise LinkedInScrapingError("Could not load LinkedIn profile (timeout)") from e
        except LinkedInScrapingError:
            raise
        except Exception as e:
            logger.exception("Scraper error")
            raise LinkedInScrapingError("Could not load LinkedIn profile") from e

    async def _scrape_once(self, url: str) -> tuple[bytes, str]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = None
            page = None
            try:
                storage_state = None
                if self._storage_state_path:
                    try:
                        if Path(self._storage_state_path).exists():
                            storage_state = self._storage_state_path
                        else:
                            logger.warning(
                                "LINKEDIN_STORAGE_STATE_PATH set but file does not exist: %s",
                                self._storage_state_path,
                            )
                    except Exception:
                        logger.exception("Failed checking storage state path")

                context = await browser.new_context(user_agent=self._user_agent, storage_state=storage_state)
                page = await context.new_page()

                # Use domcontentloaded to avoid LinkedIn long-poll causing networkidle hangs.
                await page.goto(url, wait_until=self._goto_wait_until, timeout=self._timeout_ms)
                await page.wait_for_timeout(750)

                # If we're authenticated, profile pages usually have pv-top-card. Waiting a bit
                # helps with client-side rendering and avoids capturing intermediate redirects.
                try:
                    await page.wait_for_selector(".pv-top-card", timeout=3000)
                except Exception:
                    pass

                try:
                    logger.info(
                        "Scrape page info",
                        extra={"requested_url": url, "final_url": page.url, "title": await page.title()},
                    )
                except Exception:
                    pass

                html = await page.content()
                png = await page.screenshot(full_page=True, type="png")
                return png, html
            except PlaywrightTimeoutError as e:
                # Try to dump artifacts even on timeout.
                if page is not None:
                    try:
                        self._maybe_dump_artifact(kind="html", url=url, data=await page.content(), suffix="timeout")
                        self._maybe_dump_artifact(
                            kind="screenshot",
                            url=url,
                            data=await page.screenshot(full_page=True, type="png"),
                            suffix="timeout",
                        )
                    except Exception:
                        logger.exception("Failed to dump scraper artifacts on timeout")
                raise LinkedInScrapingError("Could not load LinkedIn profile (timeout)") from e
            except Exception as e:
                # Dump artifacts on generic failure too.
                if page is not None:
                    try:
                        self._maybe_dump_artifact(kind="html", url=url, data=await page.content(), suffix="error")
                        self._maybe_dump_artifact(
                            kind="screenshot",
                            url=url,
                            data=await page.screenshot(full_page=True, type="png"),
                            suffix="error",
                        )
                    except Exception:
                        logger.exception("Failed to dump scraper artifacts on error")
                raise
            finally:
                if context is not None:
                    try:
                        await context.close()
                    except Exception:
                        pass
                await browser.close()
