from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class LinkedInProfileInsights(BaseModel):
    """Normalized insights returned from Gemini Vision for frontend display."""

    name: Optional[str] = None
    # Email handling
    # - email: "best" email to display/use (explicit preferred, else inferred if available)
    # - email_explicit: only if directly visible in screenshot/HTML
    # - email_inferred: guessed using common corporate patterns (lower confidence)
    email: Optional[str] = None
    email_explicit: Optional[str] = None
    email_inferred: Optional[str] = None
    email_inference_notes: Optional[str] = None
    current_role: Optional[str] = None
    current_company: Optional[str] = None
    unique_hooks: List[str] = Field(default_factory=list)
    portfolio_links: List[HttpUrl] = Field(default_factory=list)
    communication_style: Optional[str] = None
    suggested_angles: List[str] = Field(default_factory=list)


class RecruiterProfileDTO(BaseModel):
    recruiter_id: int
    linkedin_url: str

    insights: LinkedInProfileInsights

    confidence_score: Optional[float] = None
    enriched_at: datetime


class EnrichRecruiterRequest(BaseModel):
    linkedin_url: str


class EnrichRecruiterResponse(BaseModel):
    status: str = "ok"
    profile: RecruiterProfileDTO
