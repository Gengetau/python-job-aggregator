"""Crawl run API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CrawlRunErrorResponse(BaseModel):
    id: int
    run_id: int
    adapter_name: str
    stage: str
    target_url: str | None
    error_type: str
    message: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CrawlRunResponse(BaseModel):
    id: int
    started_at: datetime
    finished_at: datetime | None
    status: str
    trigger_type: str
    adapter_scope: str
    jobs_seen: int
    jobs_created: int
    jobs_updated: int
    jobs_deactivated: int
    errors_count: int

    model_config = ConfigDict(from_attributes=True)


class CrawlRunDetail(CrawlRunResponse):
    errors: list[CrawlRunErrorResponse] = Field(default_factory=list)


class CrawlRequest(BaseModel):
    adapters: list[str] | None = None
    options: dict[str, dict[str, Any]] = Field(default_factory=dict)


class CrawlResponse(BaseModel):
    run_id: int
    status: str
    jobs_seen: int
    jobs_created: int
    jobs_updated: int
    jobs_deactivated: int
    errors_count: int
