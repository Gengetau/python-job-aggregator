"""Greenhouse source adapter."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from job_aggregator.app.adapters.base import (
    AdapterContext,
    AdapterFetchMode,
    AdapterResult,
    BaseJobAdapter,
)
from job_aggregator.app.fetchers.http import FetchError, HttpFetcher


def _strip_html(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", cleaned).strip() or None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class GreenhouseAdapter(BaseJobAdapter):
    """Adapter boundary for Greenhouse-hosted job boards."""

    name = "greenhouse"
    fetch_mode = AdapterFetchMode.HTTP
    source_scope = "greenhouse_board_token"

    def __init__(
        self,
        *,
        board_token: str | None = None,
        company_name: str | None = None,
        fetcher: HttpFetcher | None = None,
        api_url: str | None = None,
    ) -> None:
        self.board_token = board_token
        self.company_name = company_name
        self.fetcher = fetcher
        self.api_url = api_url

    async def fetch_jobs(self, context: AdapterContext | None = None) -> AdapterResult:
        """Fetch and parse Greenhouse jobs through the public board API."""

        board_token = (
            self.board_token
            or (context.options.get("board_token") if context else None)
            or (context.scope_key if context else None)
        )
        company_name = (
            self.company_name
            or (context.options.get("company_name") if context else None)
            or board_token
            or "Unknown Company"
        )
        api_url = (
            self.api_url
            or (context.options.get("api_url") if context else None)
            or (
                f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
                if board_token
                else None
            )
        )
        if not api_url:
            return self.result(
                errors=[
                    self.error(
                        stage="configure",
                        message="Greenhouse adapter requires board_token or api_url.",
                    )
                ]
            )

        try:
            if self.fetcher is not None:
                payload = await self.fetcher.get_json(api_url)
            else:
                async with HttpFetcher() as fetcher:
                    payload = await fetcher.get_json(api_url)
        except FetchError as exc:
            return self.result(
                errors=[
                    self.error(
                        stage="fetch",
                        target_url=api_url,
                        error_type=exc.__class__.__name__,
                        message=str(exc),
                    )
                ]
            )

        return self.result(
            jobs=self.parse_payload(payload, company_name=company_name),
            next_checkpoint=datetime.now(UTC).isoformat(),
        )

    def parse_payload(self, payload: dict[str, Any], *, company_name: str) -> list:
        """Parse Greenhouse board API JSON into raw job postings."""

        jobs = []
        for item in payload.get("jobs", []):
            departments = item.get("departments") or []
            location = item.get("location") or {}
            jobs.append(
                self.raw_job(
                    source_job_id=str(item.get("id") or item.get("internal_job_id")),
                    source_url=str(item.get("absolute_url") or ""),
                    title=str(item.get("title") or ""),
                    company_name=company_name,
                    team_name=(departments[0].get("name") if departments else None),
                    location_text=location.get("name") if isinstance(location, dict) else None,
                    description_text=_strip_html(item.get("content")),
                    posted_at=_parse_datetime(item.get("updated_at")),
                    raw_payload=item,
                )
            )
        return jobs
