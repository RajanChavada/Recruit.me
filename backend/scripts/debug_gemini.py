from __future__ import annotations

"""Minimal Gemini connectivity/auth smoke test.

Why this exists:
- /api/recruiters/enrich currently returns a generic "Gemini API call failed".
- Uvicorn logs can be hard to capture when running with reload/multiple processes.
- This script isolates Gemini auth/network/model issues from scraping/DB.

Usage (from backend/):
  . .venv/bin/activate
  python scripts/debug_gemini.py

Env vars:
- GEMINI_API_KEY (required)
- GEMINI_VISION_MODEL (optional, defaults to settings.gemini_vision_model)
"""

import json
import os
import sys
import traceback

from google import genai
from google.genai import types

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.config import settings


def main() -> int:
    if not settings.gemini_api_key:
        print("ERROR: GEMINI_API_KEY is not set")
        return 2

    client = genai.Client(api_key=settings.gemini_api_key)

    try:
        resp = client.models.generate_content(
            model=settings.gemini_vision_model,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text="Return JSON only: {\"ok\": true}"),
                    ],
                )
            ],
            config=types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=50,
            ),
        )

        text = getattr(resp, "text", None)
        if text is None:
            print("Response had no .text; raw response:\n", resp)
            return 1

        print("Gemini OK. Raw text:")
        print(text)

        # Optional: confirm it's valid JSON if it looks like JSON.
        cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            parsed = json.loads(cleaned)
            print("Parsed JSON:")
            print(parsed)
        except Exception:
            pass

        return 0
    except Exception as e:
        print("Gemini FAILED")
        print("Type:", type(e).__name__)
        print("Message:", str(e))
        print("Args:", getattr(e, "args", None))
        print("Traceback:")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
