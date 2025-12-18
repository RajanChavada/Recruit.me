from __future__ import annotations

import json
import logging
from typing import Any

from google import genai
from google.genai import types
from google.genai.errors import APIError

from app.config import settings
from app.exceptions import GeminiVisionError
from app.schemas import LinkedInProfileInsights
from app.services.email_inference import generate_email_candidates


def _extract_hint_name_company(html: str) -> tuple[str | None, str | None]:
    """Cheap heuristic extraction to provide the LLM with seed name/company.

    We do not try to be perfect here. This simply helps produce email candidates
    (first.last@domain, etc.) deterministically.
    """

    if not html:
        return None, None

    lowered = html.lower()

    # Company: try og:site_name and a few linkedin meta patterns.
    company = None
    import re

    m = re.search(r"property=\"og:site_name\"\s+content=\"([^\"]+)\"", html, flags=re.IGNORECASE)
    if m:
        company = m.group(1).strip()

    # Name: try title "(8) Name | LinkedIn" or "Name - ... | LinkedIn"
    name = None
    t = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    if t:
        title = " ".join(t.group(1).split())
        # remove notification count prefix
        title = re.sub(r"^\(\d+\)\s*", "", title)
        # take everything before "| LinkedIn"
        title = re.sub(r"\s*\|\s*linkedin\s*$", "", title, flags=re.IGNORECASE)
        # take first chunk before dash if present
        name = title.split("-")[0].strip()
        if not name or len(name) > 80:
            name = None

    # If company is literally "LinkedIn", it's not helpful.
    if company and company.lower() == "linkedin":
        company = None

    # If we see "current company" label in body, we can't cheaply parse it reliably.
    # Better to leave as None than guess.

    # Basic sanity: if we failed to find a plausible name, return None.
    if name and "linkedin" in name.lower():
        name = None

    return name, company

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are an expert LinkedIn profile analyst.

Return JSON only. No markdown. No commentary.

Extract the fields in this exact schema:
{
  \"name\": string | null,
    \"email\": string | null,
    \"email_explicit\": string | null,
    \"email_inferred\": string | null,
    \"email_inference_notes\": string | null,
        "email_candidates": string[],
  \"current_role\": string | null,
  \"current_company\": string | null,
  \"unique_hooks\": string[],
  \"portfolio_links\": string[],
  \"communication_style\": string | null,
  \"suggested_angles\": string[]
}

Rules:
- If a string is unknown, return null.
- If a list is unknown/empty, return [].
- Email extraction rules:
    - If an email is explicitly visible in the screenshot/HTML, put it in "email_explicit".
    - If no explicit email is visible, you SHOULD infer a likely *corporate* email address,
        using common conventions used by companies (e.g., first.last@domain, first@domain,
        firstlast@domain, f.last@domain, firstl@domain, first_last@domain).
    - You must infer the email domain from the current company (e.g., company.com). If the domain
        is not obvious from the company name, you may guess, but clearly state uncertainty.
    - Put your best guess into "email_inferred" and explain the assumed domain + pattern used in
        "email_inference_notes".
    - IMPORTANT: If you cannot identify BOTH a likely company/domain AND the person's name with
        enough confidence to make a reasonable guess, set email_inferred=null and
        email_inference_notes=null.
    - Set "email" to the best available email: prefer email_explicit, else email_inferred, else null.
    - If you cannot infer confidently, set email_inferred to null and email_inference_notes to null.
        - Always return "email_candidates" as a list (possibly empty). If you infer a domain/pattern,
            include a few plausible candidates.
"""


class LinkedInVisionAgent:
    """Gemini Vision agent that extracts structured profile insights."""

    def __init__(self, api_key: str | None = None, model_name: str | None = None) -> None:
        self._api_key = api_key or settings.gemini_api_key
        self._model_name = model_name or settings.gemini_vision_model

        if not self._api_key:
            raise GeminiVisionError("GEMINI_API_KEY is not set")

        # REST-based Gemini client (avoids gRPC SRV DNS issues)
        self._client = genai.Client(api_key=self._api_key)

    async def analyze(
        self, *, screenshot: bytes, html: str, linkedin_url: str
    ) -> tuple[LinkedInProfileInsights, str]:
        """Analyze LinkedIn screenshot + HTML and return insights."""
        try:
            hint_name, hint_company = _extract_hint_name_company(html)
            # Provide deterministic candidates so the model can select the most plausible
            # corporate email pattern without needing external browsing.
            candidates = generate_email_candidates(name=hint_name, company=hint_company)
            candidates_block = ""
            if candidates:
                candidates_block = "\n".join([f"- {c.email} ({c.pattern})" for c in candidates[:8]])

            user_prompt = (
                f"Analyze this LinkedIn profile: {linkedin_url}\n\n"
                "Return JSON only (no code fences).\n\n"
                f"Hint (best-effort): name={hint_name!r}, company={hint_company!r}\n"
                "Email inference help:\n"
                "- You MUST copy the candidate emails shown below into the JSON field email_candidates (as strings; drop the pattern labels).\n"
                "- If email_explicit is null, and candidates exist, choose the single best guess as email_inferred (and email).\n"
                "- If candidates are empty or name/company/domain is unclear, leave email_inferred null and email_candidates [].\n"
                "Candidates:\n"
                f"{candidates_block if candidates_block else '- (no candidates generated yet)'}\n\n"
                "HTML context (may be partial):\n"
                f"{html[:12000]}\n"
            )

            raw_text = (await self._call_model(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt, screenshot=screenshot)).strip()
            parsed = self._parse_json(raw_text)
            insights = LinkedInProfileInsights.model_validate(parsed)

            # MVP guarantee: if the model didn't populate candidates, provide deterministic ones.
            if not insights.email_candidates:
                insights.email_candidates = [c.email for c in candidates]

            # If model didn't infer but we have candidates, pick the most common format first.
            if insights.email_explicit is None and insights.email_inferred is None and insights.email_candidates:
                insights.email_inferred = insights.email_candidates[0]
                insights.email_inference_notes = (
                    "Inferred using common corporate email pattern candidates generated from name/company. "
                    "This is a best-effort guess; verify before sending."
                )

            # Ensure top-level email follows our precedence.
            if insights.email is None:
                insights.email = insights.email_explicit or insights.email_inferred
            return insights, raw_text
        except GeminiVisionError:
            raise
        except Exception as e:
            logger.exception("Gemini analyze failed")
            raise GeminiVisionError("Could not analyze profile") from e

    async def _call_model(self, *, system_prompt: str, user_prompt: str, screenshot: bytes) -> str:
        try:
            # google-genai is sync; run it in a thread to keep async FastAPI path responsive.
            def _invoke() -> str:
                resp = self._client.models.generate_content(
                    model=self._model_name,
                    contents=[
                        types.Content(
                            role="user",
                            parts=[
                                types.Part.from_text(text=system_prompt),
                                types.Part.from_text(text=user_prompt),
                                types.Part.from_bytes(data=screenshot, mime_type="image/png"),
                            ],
                        )
                    ],
                    config=types.GenerateContentConfig(
                        # We enforce timeouts at the transport/thread layer (see below).
                        temperature=0.2,
                        max_output_tokens=1200,
                    ),
                )
                # google-genai responses usually expose `.text`, but be defensive.
                text = getattr(resp, "text", None)
                if isinstance(text, str):
                    return text.strip()
                # Fall back to stringification for unexpected shapes.
                return str(resp).strip()

            import asyncio

            return await asyncio.wait_for(
                _to_thread(_invoke),
                timeout=settings.gemini_timeout_seconds,
            )
        except APIError as e:
            # Bubble up something actionable (model not found, quota exceeded, auth, etc.)
            # without dumping the entire response body into the HTTP response.
            msg = str(e)
            # Truncate in case the SDK embeds large payloads.
            if len(msg) > 500:
                msg = msg[:500] + "…"
            logger.exception(
                "Gemini API error",
                extra={
                    "model": self._model_name,
                    "timeout_seconds": settings.gemini_timeout_seconds,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise GeminiVisionError(msg) from e
        except Exception as e:
            logger.exception(
                "Gemini API call failed",
                extra={
                    "model": self._model_name,
                    "timeout_seconds": settings.gemini_timeout_seconds,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "error_args": getattr(e, "args", None),
                },
            )
            raise GeminiVisionError("Gemini API call failed") from e

    def _parse_json(self, raw_text: str) -> dict:
        cleaned = raw_text.strip()
        cleaned = cleaned.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error("Gemini returned invalid JSON", extra={"raw": raw_text[:5000]})
            raise GeminiVisionError("Could not parse Gemini JSON") from e


async def _to_thread(fn, *args, **kwargs):
    """Run a blocking function in a thread."""
    import asyncio

    return await asyncio.to_thread(fn, *args, **kwargs)
