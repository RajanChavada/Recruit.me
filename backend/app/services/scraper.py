from __future__ import annotations

import asyncio
import logging

from playwright.async_api import async_playwright

from app.config import settings
from app.exceptions import LinkedInScrapingError
from app.utils import validate_linkedin_profile_url

logger = logging.getLogger(__name__)


class LinkedInScraper:
    """Scrape LinkedIn profile pages using Playwright.

    For MVP we only support a manual trigger flow (no scheduling).
    """

    def __init__(self) -> None:
        self._timeout_ms = int(settings.scraper_timeout_seconds * 1000)
        self._user_agent = settings.scraper_user_agent

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
        return await self._run_with_retry(lambda: self._screenshot_once(normalized))

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
        return await self._run_with_retry(lambda: self._html_once(normalized))

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

    async def _screenshot_once(self, url: str) -> bytes:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                context = await browser.new_context(user_agent=self._user_agent)
                page = await context.new_page()
                await page.goto(url, wait_until="networkidle", timeout=self._timeout_ms)
                await page.wait_for_timeout(500)
                return await page.screenshot(full_page=True, type="png")
            finally:
                await browser.close()

    async def _html_once(self, url: str) -> str:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                context = await browser.new_context(user_agent=self._user_agent)
                page = await context.new_page()
                await page.goto(url, wait_until="networkidle", timeout=self._timeout_ms)
                await page.wait_for_timeout(250)
                return await page.content()
            finally:
                await browser.close()
