from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.agents.linkedin_vision_agent import LinkedInVisionAgent
from app.exceptions import GeminiVisionError, LinkedInScrapingError
from app.models import RecruiterTarget
from app.services.enrichment import EnrichmentService
from app.services.scraper import LinkedInScraper

logger = logging.getLogger(__name__)


class BatchEnrichmentService:
    """Batch runner that processes queued RecruiterTarget rows."""

    def __init__(self, *, db: Session) -> None:
        self._db = db

    async def run_once(self, *, limit: int = 10) -> dict:
        # Grab pending targets.
        targets = (
            self._db.query(RecruiterTarget)
            .filter(RecruiterTarget.status == "pending")
            .order_by(RecruiterTarget.id.asc())
            .limit(limit)
            .all()
        )

        attempted = len(targets)
        succeeded = 0
        failed = 0

        # Reuse single instances for the batch.
        scraper = LinkedInScraper()
        agent = LinkedInVisionAgent()
        enrich = EnrichmentService(db=self._db, scraper=scraper, agent=agent)

        for t in targets:
            t.status = "running"
            t.last_error = None
            self._db.commit()

            try:
                await enrich.enrich_from_linkedin(t.linkedin_url)
                t.status = "succeeded"
                t.last_enriched_at = datetime.utcnow()
                succeeded += 1
            except (LinkedInScrapingError, GeminiVisionError) as e:
                t.status = "failed"
                t.last_error = str(e)
                failed += 1
            except Exception as e:
                logger.exception("Unexpected batch enrich failure", extra={"url": t.linkedin_url})
                t.status = "failed"
                t.last_error = f"Unexpected error: {type(e).__name__}"
                failed += 1

            self._db.commit()

        return {"attempted": attempted, "succeeded": succeeded, "failed": failed}
