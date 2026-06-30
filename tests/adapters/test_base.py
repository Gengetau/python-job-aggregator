import pytest
from pydantic import ValidationError

from job_aggregator.app.adapters import (
    AdapterContext,
    AdapterFetchMode,
    AdapterResult,
    BaseJobAdapter,
    CustomPageAdapter,
    GreenhouseAdapter,
    LeverAdapter,
    RawJobPosting,
)
from tests.adapters.fakes import FakeJobAdapter


async def enumerate_jobs(adapter: BaseJobAdapter) -> AdapterResult:
    return await adapter.fetch_jobs(AdapterContext(scope_key="fixture-company"))


@pytest.mark.asyncio
async def test_fake_adapter_can_enumerate_jobs_through_base_contract() -> None:
    adapter = FakeJobAdapter()

    result = await enumerate_jobs(adapter)

    assert result.adapter_name == "fake"
    assert result.jobs_count == 1
    assert result.errors_count == 0
    assert result.jobs[0].source_name == "fake"
    assert result.jobs[0].source_job_id == "fake-1"
    assert adapter.seen_context is not None
    assert adapter.seen_context.scope_key == "fixture-company"


def test_adapter_metadata_declares_name_fetch_mode_and_scope() -> None:
    adapter = FakeJobAdapter()

    metadata = adapter.metadata

    assert metadata.name == "fake"
    assert metadata.fetch_mode == AdapterFetchMode.HTTP
    assert metadata.source_scope == "fixture"


def test_raw_job_posting_requires_source_identity_and_title() -> None:
    with pytest.raises(ValidationError):
        RawJobPosting(
            source_name="fake",
            source_job_id="",
            source_url="https://example.com/jobs/empty",
            title="",
            company_name="Example Co",
        )


def test_adapter_error_is_recoverable_by_default() -> None:
    adapter = FakeJobAdapter()

    error = adapter.error(
        stage="parse",
        target_url="https://example.com/jobs",
        message="Missing job list container",
    )

    assert error.adapter_name == "fake"
    assert error.recoverable is True


def test_real_adapters_share_base_interface() -> None:
    adapters: list[BaseJobAdapter] = [
        GreenhouseAdapter(),
        LeverAdapter(),
        CustomPageAdapter(),
    ]

    assert [adapter.metadata.name for adapter in adapters] == [
        "greenhouse",
        "lever",
        "custom_page",
    ]
    assert [adapter.metadata.fetch_mode for adapter in adapters] == [
        AdapterFetchMode.HTTP,
        AdapterFetchMode.HTTP,
        AdapterFetchMode.HYBRID,
    ]
