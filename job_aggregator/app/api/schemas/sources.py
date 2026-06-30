"""Source API schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SourceSummary(BaseModel):
    source_name: str
    jobs_count: int
    latest_seen_at: datetime | None
