"""Read-only dedupe candidate routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from job_aggregator.app.api.deps import get_db
from job_aggregator.app.api.schemas.dedupe import DedupeCandidateGroupResponse
from job_aggregator.app.db.repositories.jobs import JobsRepository

router = APIRouter(prefix="/dedupe", tags=["dedupe"])


@router.get("/candidates", response_model=list[DedupeCandidateGroupResponse])
def list_dedupe_candidates(
    limit: int = Query(default=50, ge=1, le=100),
    scanned_limit: int = Query(default=1000, ge=1, le=5000),
    include_inactive: bool = Query(default=False),
    session: Session = Depends(get_db),
) -> list[DedupeCandidateGroupResponse]:
    """Return conservative cross-source duplicate candidates for operator review."""

    candidates = JobsRepository(session).duplicate_candidates(
        limit=limit,
        scanned_limit=scanned_limit,
        active_only=not include_inactive,
    )
    return [DedupeCandidateGroupResponse.model_validate(candidate) for candidate in candidates]
