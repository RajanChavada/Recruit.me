from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.agents.linkedin_vision_agent import LinkedInVisionAgent
from app.exceptions import GeminiVisionError, LinkedInScrapingError
from app.models import Recruiter, RecruiterProfile
from app.schemas import LinkedInProfileInsights, RecruiterProfileDTO
from app.services.scraper import LinkedInScraper
from app.utils import validate_linkedin_profile_url

logger = logging.getLogger(__name__)


class EnrichmentService:
    """Orchestrates scrape -> Gemini -> DB save for the MVP."""

    def __init__(self, *, db: Session, scraper: LinkedInScraper, agent: LinkedInVisionAgent) -> None:
        self._db = db
        self._scraper = scraper
        self._agent = agent

    async def enrich_from_linkedin(self, url: str) -> RecruiterProfileDTO:
        """Scrape LinkedIn + analyze with Gemini + store results.

        MVP scope: manual trigger only. No scheduling.
        """
        linkedin_url = validate_linkedin_profile_url(url)

        logger.info("Starting enrichment", extra={"url": linkedin_url})

        try:
            screenshot = await self._scraper.screenshot_linkedin(linkedin_url)
            html = await self._scraper.fetch_html(linkedin_url)
            insights, raw = await self._agent.analyze(
                screenshot=screenshot,
                html=html,
                linkedin_url=linkedin_url,
            )
        except (LinkedInScrapingError, GeminiVisionError):
            # Preserve the specific error message so the API caller sees an actionable reason.
            raise
        except Exception as e:
            logger.exception("Enrichment failed")
            # Don't mask unexpected failures as Gemini errors; keep this generic but accurate.
            raise GeminiVisionError("Could not enrich profile") from e

        recruiter = self._db.query(Recruiter).filter(Recruiter.linkedin_url == linkedin_url).one_or_none()
        if recruiter is None:
            recruiter = Recruiter(linkedin_url=linkedin_url)
            self._db.add(recruiter)
            self._db.flush()

        # Store top-level convenience fields on Recruiter for easy frontend use.
        recruiter.name = insights.name
        recruiter.email = insights.email_explicit or insights.email_inferred or insights.email
        recruiter.current_role = insights.current_role
        recruiter.current_company = insights.current_company

        profile = self._db.query(RecruiterProfile).filter(RecruiterProfile.recruiter_id == recruiter.id).one_or_none()
        if profile is None:
            profile = RecruiterProfile(
                recruiter_id=recruiter.id,
                insights=insights.model_dump(mode="json"),
                raw_gemini_response=raw,
                confidence_score=None,
                enriched_at=datetime.utcnow(),
            )
            self._db.add(profile)
        else:
            profile.insights = insights.model_dump(mode="json")
            profile.raw_gemini_response = raw
            profile.enriched_at = datetime.utcnow()

        self._db.commit()
        self._db.refresh(profile)

        return RecruiterProfileDTO(
            recruiter_id=recruiter.id,
            linkedin_url=linkedin_url,
            insights=LinkedInProfileInsights.model_validate(profile.insights),
            confidence_score=profile.confidence_score,
            enriched_at=profile.enriched_at,
        )
