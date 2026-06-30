"""Seed deterministic demo jobs through the CLI-facing collector path."""

from __future__ import annotations

import asyncio

from job_aggregator.app.adapters.demo import DemoAdapter
from job_aggregator.app.core.config import get_settings
from job_aggregator.app.crawler.collector import Collector
from job_aggregator.app.db.session import create_session_factory, init_database


async def main() -> None:
    settings = get_settings()
    engine = init_database(settings.database_url)
    session_factory = create_session_factory(engine)
    result = await Collector(
        adapters=[DemoAdapter()],
        session_factory=session_factory,
    ).run(trigger_type="manual")
    print(f"seeded run_id={result.run_id} jobs_created={result.jobs_created}")


if __name__ == "__main__":
    asyncio.run(main())
