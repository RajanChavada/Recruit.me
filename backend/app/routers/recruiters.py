from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.linkedin_vision_agent import LinkedInVisionAgent
from app.db import get_db
from app.exceptions import GeminiVisionError, InvalidLinkedInUrlError, LinkedInScrapingError
from app.models import RecruiterTarget
from app.schemas import (
    AddRecruiterTargetRequest,
    AddRecruiterTargetResponse,
    EnrichRecruiterRequest,
    EnrichRecruiterResponse,
    RecruiterTargetDTO,
    RunBatchRequest,
    RunBatchResponse,
)
from app.services.batch import BatchEnrichmentService
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


@router.post("/targets", response_model=AddRecruiterTargetResponse)
def add_target(payload: AddRecruiterTargetRequest, db: Session = Depends(get_db)) -> AddRecruiterTargetResponse:
    url = payload.linkedin_url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="linkedin_url is required")

    existing = db.query(RecruiterTarget).filter(RecruiterTarget.linkedin_url == url).first()
    if existing:
        return AddRecruiterTargetResponse(target=RecruiterTargetDTO.model_validate(existing), created=False)

    target = RecruiterTarget(linkedin_url=url, status="pending")
    db.add(target)
    db.commit()
    db.refresh(target)
    return AddRecruiterTargetResponse(target=RecruiterTargetDTO.model_validate(target), created=True)


@router.get("/targets", response_model=list[RecruiterTargetDTO])
def list_targets(status: str | None = None, db: Session = Depends(get_db)) -> list[RecruiterTargetDTO]:
    q = db.query(RecruiterTarget).order_by(RecruiterTarget.id.desc())
    if status:
        q = q.filter(RecruiterTarget.status == status)
    rows = q.limit(500).all()
    return [RecruiterTargetDTO.model_validate(r) for r in rows]


@router.post("/batch/run", response_model=RunBatchResponse)
async def run_batch(payload: RunBatchRequest, db: Session = Depends(get_db)) -> RunBatchResponse:
    svc = BatchEnrichmentService(db=db)
    stats = await svc.run_once(limit=payload.limit)
    return RunBatchResponse(**stats)
