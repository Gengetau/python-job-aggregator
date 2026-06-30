"""Lever source adapter."""

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


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(int(value) / 1000)
    except (TypeError, ValueError, OSError):
        return None


class LeverAdapter(BaseJobAdapter):
    """Adapter boundary for Lever-hosted job boards."""

    name = "lever"
    fetch_mode = AdapterFetchMode.HTTP
    source_scope = "lever_company_slug"

    def __init__(
        self,
        *,
        company_slug: str | None = None,
        company_name: str | None = None,
        fetcher: HttpFetcher | None = None,
        api_url: str | None = None,
    ) -> None:
        self.company_slug = company_slug
        self.company_name = company_name
        self.fetcher = fetcher
        self.api_url = api_url

    async def fetch_jobs(self, context: AdapterContext | None = None) -> AdapterResult:
        """Fetch and parse Lever jobs through the public postings API."""

        company_slug = (
            self.company_slug
            or (context.options.get("company_slug") if context else None)
            or (context.scope_key if context else None)
        )
        company_name = (
            self.company_name
            or (context.options.get("company_name") if context else None)
            or company_slug
            or "Unknown Company"
        )
        api_url = (
            self.api_url
            or (context.options.get("api_url") if context else None)
            or (
                f"https://api.lever.co/v0/postings/{company_slug}?mode=json"
                if company_slug
                else None
            )
        )
        if not api_url:
            return self.result(
                errors=[
                    self.error(
                        stage="configure",
                        message="Lever adapter requires company_slug or api_url.",
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

    def parse_payload(self, payload: list[dict[str, Any]], *, company_name: str) -> list:
        """Parse Lever postings JSON into raw job postings."""

        jobs = []
        for item in payload:
            categories = item.get("categories") or {}
            jobs.append(
                self.raw_job(
                    source_job_id=str(item.get("id") or item.get("text")),
                    source_url=str(item.get("hostedUrl") or item.get("applyUrl") or ""),
                    title=str(item.get("text") or ""),
                    company_name=company_name,
                    team_name=categories.get("team"),
                    location_text=categories.get("location"),
                    employment_type_text=categories.get("commitment"),
                    description_text=item.get("descriptionPlain")
                    or _strip_html(item.get("description")),
                    posted_at=_parse_timestamp(item.get("createdAt")),
                    raw_payload=item,
                )
            )
        return jobs
