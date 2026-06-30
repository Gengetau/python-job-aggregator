"""Dedupe candidate API schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class DedupeCandidateJobResponse(BaseModel):
    id: int
    source_name: str
    source_job_id: str
    source_url: str
    title: str
    company_name: str
    location_text: str | None

    model_config = ConfigDict(from_attributes=True)


class DedupeCandidateGroupResponse(BaseModel):
    fingerprint: str
    confidence: float
    reason: str
    jobs: list[DedupeCandidateJobResponse]

    model_config = ConfigDict(from_attributes=True)
