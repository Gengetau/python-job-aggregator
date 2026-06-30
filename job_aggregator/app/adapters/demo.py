"""Deterministic demo adapter for local development and tests."""

from __future__ import annotations

from job_aggregator.app.adapters.base import (
    AdapterContext,
    AdapterFetchMode,
    AdapterResult,
    BaseJobAdapter,
)


class DemoAdapter(BaseJobAdapter):
    """Emit stable example jobs without network access."""

    name = "demo"
    fetch_mode = AdapterFetchMode.HTTP
    source_scope = "fixture"

    async def fetch_jobs(self, context: AdapterContext | None = None) -> AdapterResult:
        """Return deterministic sample jobs."""

        return self.result(
            jobs=[
                self.raw_job(
                    source_job_id="demo-1",
                    source_url="https://example.com/jobs/demo-1",
                    title="Senior Python Engineer - Remote",
                    company_name="Acme Analytics",
                    team_name="Platform",
                    location_text="Remote - United States",
                    employment_type_text="Full-time",
                    salary_text="$140k - $170k",
                    description_text="Build FastAPI services and data ingestion pipelines.",
                    tags=["python", "backend"],
                    raw_payload={"fixture": "demo-1"},
                ),
                self.raw_job(
                    source_job_id="demo-2",
                    source_url="https://example.com/jobs/demo-2",
                    title="Data Platform Engineer",
                    company_name="Northstar Labs",
                    team_name="Data",
                    location_text="Hybrid / New York, NY",
                    employment_type_text="Full-time",
                    salary_text="USD 130000 - 160000",
                    description_text="Own ETL quality and data platform reliability.",
                    tags=["data", "platform"],
                    raw_payload={"fixture": "demo-2"},
                ),
            ],
            next_checkpoint="demo-complete",
        )
