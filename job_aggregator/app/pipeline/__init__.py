"""Normalization and deduplication pipeline package."""

from job_aggregator.app.pipeline.dedupe import (
    deactivate_stale_jobs,
    upsert_canonical_job,
)
from job_aggregator.app.pipeline.normalize import (
    CanonicalJobData,
    canonical_fingerprint,
    classify_employment_type,
    classify_location_type,
    clean_company,
    clean_title,
    normalize_job,
    parse_salary,
    stable_hash,
)

__all__ = [
    "CanonicalJobData",
    "canonical_fingerprint",
    "classify_employment_type",
    "classify_location_type",
    "clean_company",
    "clean_title",
    "deactivate_stale_jobs",
    "normalize_job",
    "parse_salary",
    "stable_hash",
    "upsert_canonical_job",
]
