"""Repository for crawl run lifecycle records."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from job_aggregator.app.db.models import CrawlRun, CrawlRunError


class RunsRepository:
    """Persistence operations for crawl runs and recoverable errors."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_run(
        self,
        *,
        trigger_type: str = "manual",
        adapter_scope: str = "all",
    ) -> CrawlRun:
        """Create a running crawl run."""

        run = CrawlRun(
            status="running",
            trigger_type=trigger_type,
            adapter_scope=adapter_scope,
        )
        self.session.add(run)
        self.session.flush()
        return run

    def get(self, run_id: int) -> CrawlRun | None:
        """Return a crawl run by primary key."""

        return self.session.get(CrawlRun, run_id)

    def list(self, *, limit: int = 20, offset: int = 0) -> Sequence[CrawlRun]:
        """Return recent crawl runs."""

        statement = (
            select(CrawlRun)
            .order_by(CrawlRun.started_at.desc(), CrawlRun.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def finish_run(
        self,
        run: CrawlRun,
        *,
        status: str,
        jobs_seen: int = 0,
        jobs_created: int = 0,
        jobs_updated: int = 0,
        jobs_deactivated: int = 0,
    ) -> CrawlRun:
        """Mark a run as finished with summary counters."""

        run.status = status
        run.finished_at = datetime.now(UTC)
        run.jobs_seen = jobs_seen
        run.jobs_created = jobs_created
        run.jobs_updated = jobs_updated
        run.jobs_deactivated = jobs_deactivated
        self.session.flush()
        return run

    def record_error(
        self,
        run: CrawlRun,
        *,
        adapter_name: str,
        stage: str,
        message: str,
        error_type: str = "AdapterError",
        target_url: str | None = None,
    ) -> CrawlRunError:
        """Attach a recoverable error to a crawl run."""

        error = CrawlRunError(
            run=run,
            adapter_name=adapter_name,
            stage=stage,
            target_url=target_url,
            error_type=error_type,
            message=message,
        )
        run.errors_count += 1
        self.session.add(error)
        self.session.flush()
        return error
