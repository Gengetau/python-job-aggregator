import pytest

from job_aggregator.app.adapters.base import AdapterContext, AdapterResult, BaseJobAdapter
from job_aggregator.app.crawler.collector import Collector
from job_aggregator.app.db.models import Base
from job_aggregator.app.db.repositories.jobs import JobsRepository
from job_aggregator.app.db.repositories.runs import RunsRepository
from job_aggregator.app.db.session import create_session_factory, make_engine
from tests.adapters.fakes import FakeJobAdapter


@pytest.fixture()
def session_factory():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return create_session_factory(engine)


class FailingAdapter(BaseJobAdapter):
    name = "failing"

    async def fetch_jobs(self, context: AdapterContext | None = None) -> AdapterResult:
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_collector_persists_successful_run(session_factory) -> None:
    collector = Collector(adapters=[FakeJobAdapter()], session_factory=session_factory)

    result = await collector.run()

    with session_factory() as session:
        jobs = JobsRepository(session)
        runs = RunsRepository(session)
        run = runs.get(result.run_id)

        assert result.status == "success"
        assert jobs.count() == 1
        assert run is not None
        assert run.jobs_seen == 1
        assert run.jobs_created == 1


@pytest.mark.asyncio
async def test_collector_isolates_adapter_failures(session_factory) -> None:
    collector = Collector(
        adapters=[FailingAdapter(), FakeJobAdapter()],
        session_factory=session_factory,
    )

    result = await collector.run()

    with session_factory() as session:
        runs = RunsRepository(session)
        run = runs.get(result.run_id)

        assert result.status == "partial_success"
        assert run is not None
        assert run.errors_count == 1
