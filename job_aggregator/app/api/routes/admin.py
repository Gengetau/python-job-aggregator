"""Admin routes for local crawl control."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Request

from job_aggregator.app.api.schemas.runs import CrawlRequest, CrawlResponse
from job_aggregator.app.crawler.collector import Collector

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/crawl", response_model=CrawlResponse)
async def run_crawl(payload: CrawlRequest, request: Request) -> CrawlResponse:
    """Trigger a local crawl run."""

    adapter_names = set(payload.adapters) if payload.adapters else None
    collector = Collector(
        adapters=request.app.state.adapters,
        session_factory=request.app.state.session_factory,
    )
    result = await collector.run(adapter_names=adapter_names, trigger_type="api")
    return CrawlResponse(**asdict(result))
