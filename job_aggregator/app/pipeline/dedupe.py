"""Conservative deduplication helpers."""

from __future__ import annotations

from datetime import datetime

from job_aggregator.app.db.models import Job
from job_aggregator.app.db.repositories.jobs import JobsRepository
from job_aggregator.app.pipeline.normalize import CanonicalJobData


def upsert_canonical_job(
    repository: JobsRepository,
    job_data: CanonicalJobData,
) -> tuple[Job, str]:
    """Upsert by hard source identity and preserve canonical fingerprint."""

    return repository.upsert_by_source_identity(job_data.to_repository_values())


def deactivate_stale_jobs(
    repository: JobsRepository,
    *,
    source_name: str | None = None,
    seen_before: datetime,
) -> int:
    """Deactivate jobs that have not been seen since a threshold."""

    return repository.deactivate_stale(source_name=source_name, seen_before=seen_before)
