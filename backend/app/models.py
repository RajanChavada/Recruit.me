from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Recruiter(Base):
    __tablename__ = "recruiters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    linkedin_url: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)

    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    current_role: Mapped[str | None] = mapped_column(String(200), nullable=True)
    current_company: Mapped[str | None] = mapped_column(String(200), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    profile: Mapped["RecruiterProfile"] = relationship(
        back_populates="recruiter", uselist=False, cascade="all, delete-orphan"
    )


class RecruiterProfile(Base):
    __tablename__ = "recruiter_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recruiter_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("recruiters.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    insights: Mapped[dict] = mapped_column(JSONB, nullable=False)

    confidence_score: Mapped[float | None] = mapped_column(nullable=True)
    raw_gemini_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    enriched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    recruiter: Mapped[Recruiter] = relationship(back_populates="profile")


class RecruiterTarget(Base):
    """A queue of LinkedIn URLs we want to enrich (batch/scheduled jobs).

    This allows you to:
    - store "people of interest" (recruiters, hiring managers, etc.)
    - run a batch job that enriches pending items
    - persist status + failure reasons
    """

    __tablename__ = "recruiter_targets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    linkedin_url: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)

    # pending -> running -> succeeded|failed
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)

    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_enriched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
