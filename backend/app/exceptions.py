class LinkedInScrapingError(Exception):
    """Raised when LinkedIn profile fetch fails."""


class GeminiVisionError(Exception):
    """Raised when Gemini Vision API call fails or response can't be parsed."""


class InvalidLinkedInUrlError(ValueError):
    """Raised when a provided LinkedIn URL is invalid."""
