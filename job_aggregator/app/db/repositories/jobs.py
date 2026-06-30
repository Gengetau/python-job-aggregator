"""Repository for canonical jobs."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from job_aggregator.app.db.models import Job


@dataclass(frozen=True, slots=True)
class DedupeCandidateJob:
    """Stored job summary included in a duplicate candidate group."""

    id: int
    source_name: str
    source_job_id: str
    source_url: str
    title: str
    company_name: str
    location_text: str | None


@dataclass(frozen=True, slots=True)
class DedupeCandidateGroup:
    """Conservative cross-source duplicate candidate group."""

    fingerprint: str
    confidence: float
    reason: str
    jobs: list[DedupeCandidateJob]


def _candidate_part(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip().lower()


def _candidate_key(job: Job) -> tuple[str, str, str] | None:
    title = _candidate_part(job.title)
    company_name = _candidate_part(job.company_name)
    location_text = _candidate_part(job.location_text)
    if not title or not company_name:
        return None
    return title, company_name, location_text


def _candidate_fingerprint(key: tuple[str, str, str]) -> str:
    return hashlib.sha256("|".join(key).encode("utf-8")).hexdigest()


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
        now = values.get("last_seen_at") or datetime.now(UTC)

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

    def duplicate_candidates(
        self,
        *,
        limit: int = 50,
        scanned_limit: int = 1000,
        active_only: bool = True,
    ) -> list[DedupeCandidateGroup]:
        """Return conservative cross-source duplicate candidates.

        The stored canonical fingerprint intentionally includes URL family, so this
        query uses a narrower operator review key that ignores source URL family and
        only groups exact normalized title, company, and location matches.
        """

        statement = select(Job)
        if active_only:
            statement = statement.where(Job.is_active.is_(True))
        statement = statement.order_by(Job.company_name.asc(), Job.title.asc(), Job.id.asc()).limit(
            scanned_limit
        )

        grouped: dict[tuple[str, str, str], list[Job]] = {}
        for job in self.session.scalars(statement):
            key = _candidate_key(job)
            if key is None:
                continue
            grouped.setdefault(key, []).append(job)

        candidates: list[DedupeCandidateGroup] = []
        for key, jobs in grouped.items():
            if len(jobs) < 2 or len({job.source_name for job in jobs}) < 2:
                continue

            sorted_jobs = sorted(jobs, key=lambda job: (job.source_name, job.source_job_id, job.id))
            has_location = bool(key[2])
            candidates.append(
                DedupeCandidateGroup(
                    fingerprint=_candidate_fingerprint(key),
                    confidence=0.95 if has_location else 0.85,
                    reason=(
                        "same normalized title, company, and location across multiple sources"
                        if has_location
                        else "same normalized title and company across multiple sources"
                    ),
                    jobs=[
                        DedupeCandidateJob(
                            id=job.id,
                            source_name=job.source_name,
                            source_job_id=job.source_job_id,
                            source_url=job.source_url,
                            title=job.title,
                            company_name=job.company_name,
                            location_text=job.location_text,
                        )
                        for job in sorted_jobs
                    ],
                )
            )

        return sorted(
            candidates,
            key=lambda group: (-group.confidence, group.jobs[0].company_name, group.jobs[0].title),
        )[:limit]

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
