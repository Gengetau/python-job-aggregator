"""Repository for canonical jobs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from job_aggregator.app.db.models import Job


class JobsRepository:
    """Persistence operations for normalized jobs."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, **values: Any) -> Job:
        """Create and flush a job record."""

        job = Job(**values)
        self.session.add(job)
        self.session.flush()
        return job

    def get(self, job_id: int) -> Job | None:
        """Return a job by primary key."""

        return self.session.get(Job, job_id)

    def get_by_source_identity(self, source_name: str, source_job_id: str) -> Job | None:
        """Return the same-source job identified by adapter name and source id."""

        statement = select(Job).where(
            Job.source_name == source_name,
            Job.source_job_id == source_job_id,
        )
        return self.session.scalar(statement)

    def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        source_name: str | None = None,
        company_name: str | None = None,
        q: str | None = None,
        location: str | None = None,
        location_type: str | None = None,
        employment_type: str | None = None,
        posted_after: datetime | None = None,
        is_active: bool | None = None,
        sort: str = "newest",
    ) -> Sequence[Job]:
        """List jobs with API-friendly filters."""

        statement = select(Job)
        if q is not None:
            like_value = f"%{q.lower()}%"
            statement = statement.where(
                or_(
                    func.lower(Job.title).like(like_value),
                    func.lower(Job.company_name).like(like_value),
                    func.lower(Job.description_text).like(like_value),
                )
            )
        if source_name is not None:
            statement = statement.where(Job.source_name == source_name)
        if company_name is not None:
            statement = statement.where(func.lower(Job.company_name) == company_name.lower())
        if location is not None:
            statement = statement.where(func.lower(Job.location_text).like(f"%{location.lower()}%"))
        if location_type is not None:
            statement = statement.where(Job.location_type == location_type)
        if employment_type is not None:
            statement = statement.where(Job.employment_type == employment_type)
        if posted_after is not None:
            statement = statement.where(Job.posted_at >= posted_after)
        if is_active is not None:
            statement = statement.where(Job.is_active.is_(is_active))

        if sort == "oldest":
            statement = statement.order_by(Job.posted_at.asc().nullslast(), Job.id.asc())
        elif sort == "company":
            statement = statement.order_by(Job.company_name.asc(), Job.title.asc(), Job.id.asc())
        else:
            statement = statement.order_by(Job.posted_at.desc().nullslast(), Job.id.desc())

        statement = statement.offset(offset).limit(limit)
        return list(self.session.scalars(statement))

    def count(
        self,
        *,
        source_name: str | None = None,
        company_name: str | None = None,
        q: str | None = None,
        location: str | None = None,
        location_type: str | None = None,
        employment_type: str | None = None,
        posted_after: datetime | None = None,
        is_active: bool | None = None,
    ) -> int:
        """Return stored job count with API-friendly filters."""

        statement = select(func.count()).select_from(Job)
        if q is not None:
            like_value = f"%{q.lower()}%"
            statement = statement.where(
                or_(
                    func.lower(Job.title).like(like_value),
                    func.lower(Job.company_name).like(like_value),
                    func.lower(Job.description_text).like(like_value),
                )
            )
        if source_name is not None:
            statement = statement.where(Job.source_name == source_name)
        if company_name is not None:
            statement = statement.where(func.lower(Job.company_name) == company_name.lower())
        if location is not None:
            statement = statement.where(func.lower(Job.location_text).like(f"%{location.lower()}%"))
        if location_type is not None:
            statement = statement.where(Job.location_type == location_type)
        if employment_type is not None:
            statement = statement.where(Job.employment_type == employment_type)
        if posted_after is not None:
            statement = statement.where(Job.posted_at >= posted_after)
        if is_active is not None:
            statement = statement.where(Job.is_active.is_(is_active))
        return self.session.scalar(statement) or 0

    def upsert_by_source_identity(self, values: Mapping[str, Any]) -> tuple[Job, str]:
        """Create or update a job by hard same-source identity."""

        source_name = str(values["source_name"])
        source_job_id = str(values["source_job_id"])
        existing = self.get_by_source_identity(source_name, source_job_id)
        now = values.get("last_seen_at") or datetime.now(timezone.utc)

        if existing is None:
            create_values = dict(values)
            create_values.setdefault("scraped_at", now)
            create_values.setdefault("last_seen_at", now)
            return self.create(**create_values), "created"

        previous_hash = existing.raw_hash
        for field_name, value in values.items():
            if hasattr(existing, field_name):
                setattr(existing, field_name, value)
        existing.last_seen_at = now
        self.session.flush()

        status = "updated" if existing.raw_hash != previous_hash else "unchanged"
        return existing, status

    def deactivate_stale(
        self,
        *,
        seen_before: datetime,
        source_name: str | None = None,
    ) -> int:
        """Deactivate active jobs last seen before a timestamp."""

        statement = select(Job).where(
            Job.is_active.is_(True),
            Job.last_seen_at < seen_before,
        )
        if source_name is not None:
            statement = statement.where(Job.source_name == source_name)

        jobs = list(self.session.scalars(statement))
        for job in jobs:
            job.is_active = False
        self.session.flush()
        return len(jobs)

    def sources(self) -> list[dict[str, object]]:
        """Return lightweight source summaries."""

        statement = (
            select(
                Job.source_name,
                func.count(Job.id).label("jobs_count"),
                func.max(Job.last_seen_at).label("latest_seen_at"),
            )
            .group_by(Job.source_name)
            .order_by(Job.source_name)
        )
        return [
            {
                "source_name": row.source_name,
                "jobs_count": row.jobs_count,
                "latest_seen_at": row.latest_seen_at,
            }
            for row in self.session.execute(statement)
        ]
