from __future__ import annotations

import base64
import json
import logging

import google.generativeai as genai

from app.config import settings
from app.exceptions import GeminiVisionError
from app.schemas import LinkedInProfileInsights

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
    - If no explicit email is visible, you MAY infer a likely work email using common patterns
        (e.g., first.last@company.com, first@company.com) *only when you can confidently identify*
        the person's name and current company/domain identity.
    - Put inferred guesses in "email_inferred" and explain the pattern and assumptions in
        "email_inference_notes".
    - Set "email" to the best available email: prefer email_explicit, else email_inferred, else null.
    - If you cannot infer confidently, set email_inferred to null and email_inference_notes to null.
"""


class LinkedInVisionAgent:
    """Gemini Vision agent that extracts structured profile insights."""

    def __init__(self, api_key: str | None = None, model_name: str | None = None) -> None:
        self._api_key = api_key or settings.gemini_api_key
        self._model_name = model_name or settings.gemini_vision_model

        if not self._api_key:
            raise GeminiVisionError("GEMINI_API_KEY is not set")

        genai.configure(api_key=self._api_key)
        self._model = genai.GenerativeModel(self._model_name)

    async def analyze(self, *, screenshot: bytes, html: str, linkedin_url: str) -> tuple[LinkedInProfileInsights, str]:
        """Analyze LinkedIn screenshot + HTML and return insights.

        Returns:
            (insights, raw_response_text)

        Raises:
            GeminiVisionError: On API or parse failures.
        """
        try:
            image_b64 = base64.b64encode(screenshot).decode("utf-8")
            user_prompt = (
                f"Analyze this LinkedIn profile: {linkedin_url}\n\n"
                "Return JSON only (no code fences).\n\n"
                "HTML context (may be partial):\n"
                f"{html[:12000]}\n"
            )

            # google-generativeai is sync; keep async surface for FastAPI by isolating call.
            response = await self._call_model(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt, image_b64=image_b64)
            raw_text = (response or "").strip()
            parsed = self._parse_json(raw_text)
            insights = LinkedInProfileInsights.model_validate(parsed)
            return insights, raw_text
        except GeminiVisionError:
            raise
        except Exception as e:
            logger.exception("Gemini analyze failed")
            raise GeminiVisionError("Could not analyze profile") from e

    async def _call_model(self, *, system_prompt: str, user_prompt: str, image_b64: str) -> str:
        try:
            # Using inline base64 image. Gemini generally accepts image bytes; client supports dict parts.
            # Keep it simple and robust: pass bytes rather than data URI.
            image_bytes = base64.b64decode(image_b64)
            result = await _to_thread(
                self._model.generate_content,
                [
                    system_prompt,
                    user_prompt,
                    {"mime_type": "image/png", "data": image_bytes},
                ],
            )
            return getattr(result, "text", None) or ""
        except Exception as e:
            logger.exception("Gemini API call failed")
            raise GeminiVisionError("Gemini API call failed") from e

    def _parse_json(self, raw_text: str) -> dict:
        # Some models sometimes wrap JSON in ```json fences. Strip those defensively.
        cleaned = raw_text.strip()
        cleaned = cleaned.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error("Gemini returned invalid JSON", extra={"raw": raw_text[:5000]})
            raise GeminiVisionError("Could not parse Gemini JSON") from e


async def _to_thread(fn, *args, **kwargs):
    """Run a blocking function in a thread (py3.9+ compatible)."""
    import asyncio

    return await asyncio.to_thread(fn, *args, **kwargs)
