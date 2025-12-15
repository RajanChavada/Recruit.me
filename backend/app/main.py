from __future__ import annotations

import logging

from fastapi import FastAPI

from app.routers.health import router as health_router
from app.routers.recruiters import router as recruiters_router

logger = logging.getLogger(__name__)

app = FastAPI(title="Recruit.me API", version="0.1.0")

app.include_router(health_router, prefix="/api")
app.include_router(recruiters_router, prefix="/api")


@app.get("/")
async def root() -> dict:
    return {"name": "Recruit.me API", "status": "ok"}
