"""Small deterministic enrichment helpers."""

from __future__ import annotations

import json

from job_aggregator.app.pipeline.normalize import CanonicalJobData


def tags_for_job(job: CanonicalJobData) -> list[str]:
    """Return parsed tags for a normalized job."""

    return list(json.loads(job.tags_json))
