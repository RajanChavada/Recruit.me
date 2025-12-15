from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.linkedin_vision_agent import LinkedInVisionAgent
from app.db import get_db
from app.exceptions import GeminiVisionError, InvalidLinkedInUrlError, LinkedInScrapingError
from app.schemas import EnrichRecruiterRequest, EnrichRecruiterResponse
from app.services.enrichment import EnrichmentService
from app.services.scraper import LinkedInScraper

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recruiters", tags=["recruiters"])


@router.post("/enrich", response_model=EnrichRecruiterResponse)
async def enrich_recruiter(request: EnrichRecruiterRequest, db: Session = Depends(get_db)) -> EnrichRecruiterResponse:
    """Manual enrichment endpoint (MVP)."""
    try:
        service = EnrichmentService(db=db, scraper=LinkedInScraper(), agent=LinkedInVisionAgent())
        profile = await service.enrich_from_linkedin(request.linkedin_url)
        return EnrichRecruiterResponse(profile=profile)
    except InvalidLinkedInUrlError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except LinkedInScrapingError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except GeminiVisionError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unhandled error")
        raise HTTPException(status_code=500, detail="Internal server error") from e
