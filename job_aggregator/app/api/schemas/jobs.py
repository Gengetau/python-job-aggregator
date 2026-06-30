"""Job API schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class JobResponse(BaseModel):
    id: int
    canonical_fingerprint: str
    source_name: str
    source_job_id: str
    source_url: str
    title: str
    company_name: str
    team_name: str | None
    location_text: str | None
    location_type: str
    employment_type: str
    salary_min: Decimal | None
    salary_max: Decimal | None
    salary_currency: str | None
    description_text: str | None
    tags_json: str
    posted_at: datetime | None
    scraped_at: datetime
    last_seen_at: datetime
    is_active: bool
    raw_hash: str

    model_config = ConfigDict(from_attributes=True)


class JobsPage(BaseModel):
    items: list[JobResponse]
    total: int
    page: int
    page_size: int
