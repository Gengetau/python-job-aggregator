"""Reusable async HTTP fetch infrastructure."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict

from job_aggregator.app.core.config import get_settings
from job_aggregator.app.fetchers.rate_limit import HostRateLimiter


class FetchError(RuntimeError):
    """Raised when a fetch operation exhausts retries."""

    def __init__(
        self,
        message: str,
        *,
        url: str,
        status_code: int | None = None,
        attempts: int = 1,
    ) -> None:
        super().__init__(message)
        self.url = url
        self.status_code = status_code
        self.attempts = attempts


class FetchResponse(BaseModel):
    """Small response wrapper independent of httpx internals."""

    url: str
    status_code: int
    text: str
    headers: dict[str, str]

    model_config = ConfigDict(extra="forbid")

    def json(self) -> Any:
        """Parse the response body as JSON."""

        import json

        return json.loads(self.text)


class HttpFetcher:
    """HTTP-first fetcher with timeout, retries, backoff, and rate limiting."""

    def __init__(
        self,
        *,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
        backoff_seconds: float | None = None,
        rate_limiter: HostRateLimiter | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        settings = get_settings()
        self.timeout_seconds = timeout_seconds or settings.http_timeout_seconds
        self.max_retries = settings.http_max_retries if max_retries is None else max_retries
        self.backoff_seconds = backoff_seconds or settings.http_backoff_seconds
        self.rate_limiter = rate_limiter or HostRateLimiter(settings.per_host_concurrency)
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> HttpFetcher:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout_seconds)
            self._owns_client = True
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        if self._client is not None and self._owns_client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Return an active HTTP client, creating one lazily."""

        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout_seconds)
            self._owns_client = True
        return self._client

    async def get(self, url: str, *, headers: dict[str, str] | None = None) -> FetchResponse:
        """Fetch a URL and return text plus metadata."""

        attempts_allowed = self.max_retries + 1
        last_error: Exception | None = None
        last_status: int | None = None

        for attempt in range(1, attempts_allowed + 1):
            try:
                async with self.rate_limiter.limit(url):
                    response = await self.client.get(url, headers=headers)
                last_status = response.status_code
                response.raise_for_status()
                return FetchResponse(
                    url=str(response.url),
                    status_code=response.status_code,
                    text=response.text,
                    headers=dict(response.headers),
                )
            except (TimeoutError, httpx.HTTPError) as exc:
                last_error = exc
                if attempt == attempts_allowed:
                    break
                await asyncio.sleep(self.backoff_seconds * (2 ** (attempt - 1)))

        message = f"Failed to fetch {url} after {attempts_allowed} attempt(s)"
        if last_error is not None:
            message = f"{message}: {last_error}"
        raise FetchError(
            message,
            url=url,
            status_code=last_status,
            attempts=attempts_allowed,
        )

    async def get_text(self, url: str, *, headers: dict[str, str] | None = None) -> str:
        """Fetch a URL and return the text body."""

        return (await self.get(url, headers=headers)).text

    async def get_json(self, url: str, *, headers: dict[str, str] | None = None) -> Any:
        """Fetch a URL and parse the body as JSON."""

        return (await self.get(url, headers=headers)).json()
