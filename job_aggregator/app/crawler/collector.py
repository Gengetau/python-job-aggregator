"""Crawl orchestration core."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from job_aggregator.app.adapters.base import AdapterContext, BaseJobAdapter
from job_aggregator.app.crawler.checkpoints import checkpoint_scope, context_with_checkpoint
from job_aggregator.app.db.repositories.checkpoints import CheckpointsRepository
from job_aggregator.app.db.repositories.jobs import JobsRepository
from job_aggregator.app.db.repositories.runs import RunsRepository
from job_aggregator.app.pipeline.dedupe import upsert_canonical_job
from job_aggregator.app.pipeline.normalize import normalize_job

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CollectorResult:
    """Return value for collector invocations."""

    run_id: int
    status: str
    jobs_seen: int
    jobs_created: int
    jobs_updated: int
    jobs_deactivated: int
    errors_count: int


class Collector:
    """Execute adapters and persist canonical crawl results."""

    def __init__(
        self,
        *,
        adapters: Iterable[BaseJobAdapter],
        session_factory: sessionmaker[Session],
    ) -> None:
        self.adapters = list(adapters)
        self.session_factory = session_factory

    async def run(
        self,
        *,
        adapter_names: set[str] | None = None,
        trigger_type: str = "manual",
        contexts: Mapping[str, AdapterContext] | None = None,
    ) -> CollectorResult:
        """Run selected adapters and persist crawl summaries."""

        selected = [
            adapter
            for adapter in self.adapters
            if adapter_names is None or adapter.name in adapter_names
        ]
        adapter_scope = ",".join(adapter.name for adapter in selected) or "none"

        with self.session_factory() as session:
            runs = RunsRepository(session)
            jobs = JobsRepository(session)
            checkpoints = CheckpointsRepository(session)
            run = runs.create_run(trigger_type=trigger_type, adapter_scope=adapter_scope)
            session.commit()

            counts = {
                "seen": 0,
                "created": 0,
                "updated": 0,
                "deactivated": 0,
            }

            for adapter in selected:
                logger.info(
                    "starting adapter crawl",
                    extra={"adapter": adapter.name, "run_id": run.id},
                )
                base_context = contexts.get(adapter.name) if contexts else None
                adapter_context = context_with_checkpoint(adapter, checkpoints, base_context)
                try:
                    result = await adapter.fetch_jobs(adapter_context)
                except Exception as exc:
                    runs.record_error(
                        run,
                        adapter_name=adapter.name,
                        stage="adapter",
                        error_type=exc.__class__.__name__,
                        message=str(exc),
                    )
                    session.commit()
                    continue

                for error in result.errors:
                    runs.record_error(
                        run,
                        adapter_name=error.adapter_name,
                        stage=error.stage,
                        target_url=error.target_url,
                        error_type=error.error_type,
                        message=error.message,
                    )

                for raw_job in result.jobs:
                    counts["seen"] += 1
                    canonical = normalize_job(raw_job)
                    _job, status = upsert_canonical_job(jobs, canonical)
                    if status == "created":
                        counts["created"] += 1
                    elif status == "updated":
                        counts["updated"] += 1

                if result.next_checkpoint:
                    checkpoints.upsert(
                        adapter_name=adapter.name,
                        scope_key=checkpoint_scope(adapter, adapter_context),
                        cursor_value=result.next_checkpoint,
                    )

                session.commit()

            final_status = self._status_for(
                errors_count=run.errors_count,
                selected_count=len(selected),
                jobs_seen=counts["seen"],
                jobs_created=counts["created"],
                jobs_updated=counts["updated"],
            )
            runs.finish_run(
                run,
                status=final_status,
                jobs_seen=counts["seen"],
                jobs_created=counts["created"],
                jobs_updated=counts["updated"],
                jobs_deactivated=counts["deactivated"],
            )
            session.commit()

            return CollectorResult(
                run_id=run.id,
                status=run.status,
                jobs_seen=run.jobs_seen,
                jobs_created=run.jobs_created,
                jobs_updated=run.jobs_updated,
                jobs_deactivated=run.jobs_deactivated,
                errors_count=run.errors_count,
            )

    @staticmethod
    def _status_for(
        *,
        errors_count: int,
        selected_count: int,
        jobs_seen: int,
        jobs_created: int,
        jobs_updated: int,
    ) -> str:
        """Choose final run status from persisted counters."""

        if selected_count == 0:
            return "failed"
        if errors_count == 0:
            return "success"
        if jobs_seen > 0 or jobs_created > 0 or jobs_updated > 0:
            return "partial_success"
        return "failed"
