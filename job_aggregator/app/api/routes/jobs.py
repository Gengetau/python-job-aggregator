"""Job query routes."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from job_aggregator.app.api.deps import get_db
from job_aggregator.app.api.schemas.jobs import JobResponse, JobsPage
from job_aggregator.app.db.repositories.jobs import JobsRepository

router = APIRouter(tags=["jobs"])


@router.get("/jobs", response_model=JobsPage)
def list_jobs(
    q: str | None = None,
    company: str | None = None,
    source: str | None = None,
    location: str | None = None,
    location_type: str | None = None,
    employment_type: str | None = None,
    posted_after: datetime | None = None,
    is_active: bool | None = True,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort: str = Query(default="newest", pattern="^(newest|oldest|company)$"),
    session: Session = Depends(get_db),
) -> JobsPage:
    """List jobs with filters and pagination."""

    repository = JobsRepository(session)
    offset = (page - 1) * page_size
    items = repository.list(
        q=q,
        company_name=company,
        source_name=source,
        location=location,
        location_type=location_type,
        employment_type=employment_type,
        posted_after=posted_after,
        is_active=is_active,
        limit=page_size,
        offset=offset,
        sort=sort,
    )
    total = repository.count(
        q=q,
        company_name=company,
        source_name=source,
        location=location,
        location_type=location_type,
        employment_type=employment_type,
        posted_after=posted_after,
        is_active=is_active,
    )
    return JobsPage(
        items=[JobResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: int, session: Session = Depends(get_db)) -> JobResponse:
    """Return a single job."""

    job = JobsRepository(session).get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.model_validate(job)
