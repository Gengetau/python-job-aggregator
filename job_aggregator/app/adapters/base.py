"""Shared source adapter contract and raw job shapes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, computed_field


def utc_now() -> datetime:
    """Return the current UTC timestamp."""

    return datetime.now(UTC)


class AdapterFetchMode(StrEnum):
    """Supported acquisition strategies declared by adapters."""

    HTTP = "http"
    BROWSER = "browser"
    HYBRID = "hybrid"


class AdapterContext(BaseModel):
    """Runtime context passed to adapters by the collector."""

    scope_key: str | None = Field(
        default=None,
        description="Optional source-specific scope, such as a company token.",
    )
    checkpoint: str | None = Field(
        default=None,
        description="Previously persisted cursor for resumable enumeration.",
    )
    options: dict[str, Any] = Field(
        default_factory=dict,
        description="Adapter-specific runtime options.",
    )

    model_config = ConfigDict(extra="forbid")


class AdapterMetadata(BaseModel):
    """Static metadata that lets the collector reason about an adapter."""

    name: str = Field(min_length=1)
    fetch_mode: AdapterFetchMode
    source_scope: str = Field(
        default="default",
        min_length=1,
        description="Human-readable scope type handled by the adapter.",
    )

    model_config = ConfigDict(frozen=True, extra="forbid")


class RawJobPosting(BaseModel):
    """Raw intermediate job shape emitted by all adapters."""

    source_name: str = Field(min_length=1)
    source_job_id: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    title: str = Field(min_length=1)
    company_name: str = Field(min_length=1)
    team_name: str | None = None
    location_text: str | None = None
    employment_type_text: str | None = None
    salary_text: str | None = None
    description_text: str | None = None
    tags: list[str] = Field(default_factory=list)
    posted_at: datetime | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    fetched_at: datetime = Field(default_factory=utc_now)

    model_config = ConfigDict(extra="forbid")


class AdapterError(BaseModel):
    """Recoverable adapter error captured without crashing the run."""

    adapter_name: str = Field(min_length=1)
    stage: str = Field(min_length=1)
    message: str = Field(min_length=1)
    error_type: str = Field(default="AdapterError", min_length=1)
    target_url: str | None = None
    recoverable: bool = True

    model_config = ConfigDict(extra="forbid")


class AdapterResult(BaseModel):
    """Jobs and recoverable errors produced by one adapter execution."""

    adapter_name: str = Field(min_length=1)
    jobs: list[RawJobPosting] = Field(default_factory=list)
    errors: list[AdapterError] = Field(default_factory=list)
    next_checkpoint: str | None = None

    model_config = ConfigDict(extra="forbid")

    @computed_field
    @property
    def jobs_count(self) -> int:
        """Return the number of raw jobs emitted."""

        return len(self.jobs)

    @computed_field
    @property
    def errors_count(self) -> int:
        """Return the number of recoverable errors emitted."""

        return len(self.errors)


class BaseJobAdapter(ABC):
    """Base class for all source adapters."""

    name: ClassVar[str]
    fetch_mode: ClassVar[AdapterFetchMode] = AdapterFetchMode.HTTP
    source_scope: ClassVar[str] = "default"

    @property
    def metadata(self) -> AdapterMetadata:
        """Return adapter metadata used by collectors and operators."""

        return AdapterMetadata(
            name=self.name,
            fetch_mode=self.fetch_mode,
            source_scope=self.source_scope,
        )

    @abstractmethod
    async def fetch_jobs(self, context: AdapterContext | None = None) -> AdapterResult:
        """Enumerate raw jobs from the source."""

    def result(
        self,
        *,
        jobs: list[RawJobPosting] | None = None,
        errors: list[AdapterError] | None = None,
        next_checkpoint: str | None = None,
    ) -> AdapterResult:
        """Build a result stamped with this adapter's name."""

        return AdapterResult(
            adapter_name=self.name,
            jobs=jobs or [],
            errors=errors or [],
            next_checkpoint=next_checkpoint,
        )

    def error(
        self,
        *,
        stage: str,
        message: str,
        error_type: str = "AdapterError",
        target_url: str | None = None,
        recoverable: bool = True,
    ) -> AdapterError:
        """Build a recoverable error stamped with this adapter's name."""

        return AdapterError(
            adapter_name=self.name,
            stage=stage,
            message=message,
            error_type=error_type,
            target_url=target_url,
            recoverable=recoverable,
        )

    def raw_job(
        self,
        *,
        source_job_id: str,
        source_url: str,
        title: str,
        company_name: str,
        team_name: str | None = None,
        location_text: str | None = None,
        employment_type_text: str | None = None,
        salary_text: str | None = None,
        description_text: str | None = None,
        tags: list[str] | None = None,
        posted_at: datetime | None = None,
        raw_payload: Mapping[str, Any] | None = None,
    ) -> RawJobPosting:
        """Build a raw job stamped with this adapter's source name."""

        return RawJobPosting(
            source_name=self.name,
            source_job_id=source_job_id,
            source_url=source_url,
            title=title,
            company_name=company_name,
            team_name=team_name,
            location_text=location_text,
            employment_type_text=employment_type_text,
            salary_text=salary_text,
            description_text=description_text,
            tags=tags or [],
            posted_at=posted_at,
            raw_payload=dict(raw_payload or {}),
        )
