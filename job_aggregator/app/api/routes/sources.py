"""Source summary routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from job_aggregator.app.api.deps import get_db
from job_aggregator.app.api.schemas.sources import SourceSummary
from job_aggregator.app.db.repositories.jobs import JobsRepository

router = APIRouter(tags=["sources"])


@router.get("/sources", response_model=list[SourceSummary])
def list_sources(session: Session = Depends(get_db)) -> list[SourceSummary]:
    """Return source summaries."""

    return [SourceSummary.model_validate(row) for row in JobsRepository(session).sources()]
