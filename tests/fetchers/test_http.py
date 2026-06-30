import httpx
import pytest

from job_aggregator.app.fetchers.http import FetchError, HttpFetcher
from job_aggregator.app.fetchers.rate_limit import HostRateLimiter


@pytest.mark.asyncio
async def test_http_fetcher_get_text_and_json() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"ok": True}, request=request)
    )
    async with httpx.AsyncClient(transport=transport) as client:
        fetcher = HttpFetcher(client=client)

        response = await fetcher.get("https://example.com/data.json")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


@pytest.mark.asyncio
async def test_http_fetcher_retries_bounded_failures() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503, text="unavailable", request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        fetcher = HttpFetcher(client=client, max_retries=2, backoff_seconds=0)

        with pytest.raises(FetchError) as exc_info:
            await fetcher.get_text("https://example.com/jobs")

    assert calls == 3
    assert exc_info.value.attempts == 3
    assert exc_info.value.status_code == 503


def test_host_rate_limiter_normalizes_host() -> None:
    assert HostRateLimiter.host_for_url("https://Example.COM/jobs") == "example.com"
