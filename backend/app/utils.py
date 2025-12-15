from __future__ import annotations

import re

from app.exceptions import InvalidLinkedInUrlError

LINKEDIN_PROFILE_URL_RE = re.compile(
    r"^https?://(www\.)?linkedin\.com/in/[A-Za-z0-9\-_%]+/?(\?.*)?$",
    re.IGNORECASE,
)


def validate_linkedin_profile_url(url: str) -> str:
    """Validate a LinkedIn profile URL.

    Args:
        url: User-provided URL.

    Returns:
        Normalized URL (stripped).

    Raises:
        InvalidLinkedInUrlError: If the URL isn't a LinkedIn /in/ profile URL.
    """
    normalized = (url or "").strip()
    if not LINKEDIN_PROFILE_URL_RE.match(normalized):
        raise InvalidLinkedInUrlError("Invalid LinkedIn URL")
    return normalized
