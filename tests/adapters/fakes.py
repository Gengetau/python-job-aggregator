"""Fake adapters used by adapter contract tests."""

from __future__ import annotations

from job_aggregator.app.adapters.base import (
    AdapterContext,
    AdapterError,
    AdapterFetchMode,
    AdapterResult,
    BaseJobAdapter,
    RawJobPosting,
)


class FakeJobAdapter(BaseJobAdapter):
    """Small deterministic adapter for tests."""

    name = "fake"
    fetch_mode = AdapterFetchMode.HTTP
    source_scope = "fixture"

    def __init__(
        self,
        *,
        jobs: list[RawJobPosting] | None = None,
        errors: list[AdapterError] | None = None,
    ) -> None:
        self._jobs = jobs
        self._errors = errors
        self.seen_context: AdapterContext | None = None

    async def fetch_jobs(self, context: AdapterContext | None = None) -> AdapterResult:
        """Return configured fixture data."""

        self.seen_context = context
        jobs = self._jobs or [
            self.raw_job(
                source_job_id="fake-1",
                source_url="https://example.com/jobs/fake-1",
                title="Python Engineer",
                company_name="Example Co",
                location_text="Remote",
                employment_type_text="Full-time",
                salary_text="$120,000 - $150,000",
                description_text="Build job aggregation systems.",
                tags=["python", "backend"],
                raw_payload={"id": "fake-1"},
            )
        ]
        return self.result(jobs=jobs, errors=self._errors)
