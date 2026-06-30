"""Async host-level rate limiting helpers."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from contextlib import asynccontextmanager
from urllib.parse import urlparse


class HostRateLimiter:
    """Bound concurrent work per host with asyncio semaphores."""

    def __init__(self, per_host_limit: int = 2) -> None:
        if per_host_limit < 1:
            raise ValueError("per_host_limit must be at least 1")
        self.per_host_limit = per_host_limit
        self._locks: dict[str, asyncio.Semaphore] = defaultdict(
            lambda: asyncio.Semaphore(self.per_host_limit)
        )

    @staticmethod
    def host_for_url(url: str) -> str:
        """Return normalized host key for a URL."""

        parsed = urlparse(url)
        return parsed.netloc.lower() or "local"

    @asynccontextmanager
    async def limit(self, url: str):
        """Acquire host capacity for a URL."""

        semaphore = self._locks[self.host_for_url(url)]
        await semaphore.acquire()
        try:
            yield
        finally:
            semaphore.release()
