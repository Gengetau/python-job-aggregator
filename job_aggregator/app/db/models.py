"""SQLAlchemy ORM models for persisted job and crawl state."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    """Return the current UTC timestamp."""

    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class Job(Base):
    """Canonical normalized job record."""

    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint(
            "source_name",
            "source_job_id",
            name="uq_jobs_source_identity",
        ),
        CheckConstraint(
            "location_type IN ('onsite', 'hybrid', 'remote', 'unknown')",
            name="ck_jobs_location_type",
        ),
        CheckConstraint(
            "employment_type IN ('full_time', 'part_time', 'contract', 'intern', 'unknown')",
            name="ck_jobs_employment_type",
        ),
        Index("ix_jobs_canonical_fingerprint", "canonical_fingerprint"),
        Index("ix_jobs_source_name", "source_name"),
        Index("ix_jobs_company_name", "company_name"),
        Index("ix_jobs_location_type", "location_type"),
        Index("ix_jobs_employment_type", "employment_type"),
        Index("ix_jobs_is_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    source_name: Mapped[str] = mapped_column(String(80), nullable=False)
    source_job_id: Mapped[str] = mapped_column(String(160), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    company_name: Mapped[str] = mapped_column(String(240), nullable=False)
    team_name: Mapped[str | None] = mapped_column(String(240), nullable=True)
    location_text: Mapped[str | None] = mapped_column(String(300), nullable=True)
    location_type: Mapped[str] = mapped_column(String(24), default="unknown", nullable=False)
    employment_type: Mapped[str] = mapped_column(String(24), default="unknown", nullable=False)
    salary_min: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    salary_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    salary_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    description_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    raw_hash: Mapped[str] = mapped_column(String(128), nullable=False)


class CrawlRun(Base):
    """Lifecycle and summary record for one crawl execution."""

    __tablename__ = "crawl_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'success', 'partial_success', 'failed')",
            name="ck_crawl_runs_status",
        ),
        CheckConstraint(
            "trigger_type IN ('manual', 'scheduled', 'api')",
            name="ck_crawl_runs_trigger_type",
        ),
        Index("ix_crawl_runs_status", "status"),
        Index("ix_crawl_runs_started_at", "started_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="running", nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(24), default="manual", nullable=False)
    adapter_scope: Mapped[str] = mapped_column(Text, default="all", nullable=False)
    jobs_seen: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_deactivated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    errors_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    errors: Mapped[list[CrawlRunError]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )
    adapter_states: Mapped[list[CrawlRunAdapterState]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )


class CrawlRunAdapterState(Base):
    """Per-adapter checkpoint state captured for one crawl run."""

    __tablename__ = "crawl_run_adapter_states"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "adapter_name",
            "scope_key",
            name="uq_crawl_run_adapter_states_run_adapter_scope",
        ),
        Index("ix_crawl_run_adapter_states_run_id", "run_id"),
        Index("ix_crawl_run_adapter_states_adapter_name", "adapter_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("crawl_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    adapter_name: Mapped[str] = mapped_column(String(80), nullable=False)
    scope_key: Mapped[str] = mapped_column(String(240), nullable=False)
    checkpoint_before: Mapped[str | None] = mapped_column(Text, nullable=True)
    checkpoint_after: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    run: Mapped[CrawlRun] = relationship(back_populates="adapter_states")


class CrawlRunError(Base):
    """Recoverable adapter or pipeline error attached to a crawl run."""

    __tablename__ = "crawl_run_errors"
    __table_args__ = (
        Index("ix_crawl_run_errors_run_id", "run_id"),
        Index("ix_crawl_run_errors_adapter_name", "adapter_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("crawl_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    adapter_name: Mapped[str] = mapped_column(String(80), nullable=False)
    stage: Mapped[str] = mapped_column(String(80), nullable=False)
    target_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_type: Mapped[str] = mapped_column(String(160), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    run: Mapped[CrawlRun] = relationship(back_populates="errors")


class SourceCheckpoint(Base):
    """Adapter checkpoint used to resume or incrementally crawl a source."""

    __tablename__ = "source_checkpoints"
    __table_args__ = (
        UniqueConstraint(
            "adapter_name",
            "scope_key",
            name="uq_source_checkpoints_adapter_scope",
        ),
        Index("ix_source_checkpoints_adapter_name", "adapter_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    adapter_name: Mapped[str] = mapped_column(String(80), nullable=False)
    scope_key: Mapped[str] = mapped_column(String(240), nullable=False)
    cursor_value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
