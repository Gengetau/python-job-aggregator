"""Crawl run routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from job_aggregator.app.api.deps import get_db
from job_aggregator.app.api.schemas.runs import CrawlRunDetail, CrawlRunResponse
from job_aggregator.app.db.repositories.runs import RunsRepository

router = APIRouter(tags=["runs"])


@router.get("/runs", response_model=list[CrawlRunResponse])
def list_runs(session: Session = Depends(get_db)) -> list[CrawlRunResponse]:
    """Return recent crawl runs."""

    return [CrawlRunResponse.model_validate(run) for run in RunsRepository(session).list()]


@router.get("/runs/{run_id}", response_model=CrawlRunDetail)
def get_run(run_id: int, session: Session = Depends(get_db)) -> CrawlRunDetail:
    """Return a crawl run with errors and adapter states."""

    run = RunsRepository(session).get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return CrawlRunDetail.model_validate(run)
