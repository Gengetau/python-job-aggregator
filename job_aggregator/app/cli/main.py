"""Typer command line entrypoint."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import typer

from job_aggregator import __version__
from job_aggregator.app.adapters import DemoAdapter, GreenhouseAdapter, LeverAdapter
from job_aggregator.app.adapters.base import BaseJobAdapter
from job_aggregator.app.crawler.collector import Collector
from job_aggregator.app.core.config import get_settings
from job_aggregator.app.core.logging import configure_logging
from job_aggregator.app.db.repositories.jobs import JobsRepository
from job_aggregator.app.db.repositories.runs import RunsRepository
from job_aggregator.app.db.session import create_session_factory, init_database

app = typer.Typer(help="Operate the Python Job Aggregator service.")
db_app = typer.Typer(help="Manage local database schema.")
crawl_app = typer.Typer(help="Run and resume crawl operations.")
jobs_app = typer.Typer(help="Maintain stored jobs.")
runs_app = typer.Typer(help="Inspect crawl runs.")
app.add_typer(db_app, name="db")
app.add_typer(crawl_app, name="crawl")
app.add_typer(jobs_app, name="jobs")
app.add_typer(runs_app, name="runs")


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        help="Show the installed package version.",
    ),
) -> None:
    """Initialize CLI runtime state."""

    settings = get_settings()
    configure_logging(settings.log_level)
    if version:
        typer.echo(__version__)
        raise typer.Exit()


@app.command()
def status() -> None:
    """Show basic local configuration status."""

    settings = get_settings()
    typer.echo(f"environment={settings.environment}")
    typer.echo(f"database_url={settings.database_url}")


def _session_factory(database_url: str | None = None):
    settings = get_settings()
    resolved_url = database_url or settings.database_url
    engine = init_database(resolved_url)
    return create_session_factory(engine), resolved_url


def _adapter_for(
    adapter_name: str | None,
    *,
    scope: str | None,
    company: str | None,
    api_url: str | None,
) -> BaseJobAdapter:
    if adapter_name == "greenhouse":
        return GreenhouseAdapter(board_token=scope, company_name=company, api_url=api_url)
    if adapter_name == "lever":
        return LeverAdapter(company_slug=scope, company_name=company, api_url=api_url)
    return DemoAdapter()


async def _run_collector(
    *,
    adapters: list[BaseJobAdapter],
    database_url: str | None = None,
    trigger_type: str = "manual",
) -> None:
    session_factory, resolved_url = _session_factory(database_url)
    result = await Collector(adapters=adapters, session_factory=session_factory).run(
        trigger_type=trigger_type
    )
    typer.echo(f"database_url={resolved_url}")
    typer.echo(f"run_id={result.run_id}")
    typer.echo(f"status={result.status}")
    typer.echo(f"jobs_seen={result.jobs_seen}")
    typer.echo(f"jobs_created={result.jobs_created}")
    typer.echo(f"jobs_updated={result.jobs_updated}")
    typer.echo(f"errors_count={result.errors_count}")


@db_app.command("init")
def init_db(
    database_url: str | None = typer.Option(
        None,
        "--database-url",
        help="Override JOB_AGGREGATOR_DATABASE_URL for this command.",
    ),
) -> None:
    """Create database tables for local development."""

    settings = get_settings()
    resolved_url = database_url or settings.database_url
    init_database(resolved_url)
    typer.echo(f"initialized database: {resolved_url}")


@db_app.command("seed-demo")
def seed_demo(
    database_url: str | None = typer.Option(
        None,
        "--database-url",
        help="Override JOB_AGGREGATOR_DATABASE_URL for this command.",
    ),
) -> None:
    """Load deterministic demo jobs through the collector path."""

    asyncio.run(
        _run_collector(
            adapters=[DemoAdapter()],
            database_url=database_url,
            trigger_type="manual",
        )
    )


@crawl_app.command("run")
def crawl_run(
    adapter: str | None = typer.Option(
        None,
        "--adapter",
        help="Adapter to run: demo, greenhouse, or lever. Defaults to demo.",
    ),
    all_adapters: bool = typer.Option(
        False,
        "--all",
        help="Run the local demo adapter set.",
    ),
    scope: str | None = typer.Option(
        None,
        "--scope",
        help="Source scope such as a Greenhouse board token or Lever company slug.",
    ),
    company: str | None = typer.Option(
        None,
        "--company",
        help="Company display name for configured source adapters.",
    ),
    api_url: str | None = typer.Option(
        None,
        "--api-url",
        help="Override source API URL, useful for fixture/demo runs.",
    ),
    database_url: str | None = typer.Option(None, "--database-url"),
) -> None:
    """Run a crawl."""

    adapters = [DemoAdapter()] if all_adapters else [_adapter_for(adapter, scope=scope, company=company, api_url=api_url)]
    asyncio.run(_run_collector(adapters=adapters, database_url=database_url))


@crawl_app.command("resume")
def crawl_resume(
    run_id: int = typer.Option(..., "--run-id", help="Run id whose checkpoint context should be resumed."),
    database_url: str | None = typer.Option(None, "--database-url"),
) -> None:
    """Resume from stored checkpoints using the local demo adapter set."""

    typer.echo(f"resuming_from_run_id={run_id}")
    asyncio.run(
        _run_collector(
            adapters=[DemoAdapter()],
            database_url=database_url,
            trigger_type="manual",
        )
    )


@jobs_app.command("dedupe")
def jobs_dedupe(
    database_url: str | None = typer.Option(None, "--database-url"),
) -> None:
    """Show conservative dedupe state."""

    session_factory, _resolved_url = _session_factory(database_url)
    with session_factory() as session:
        repository = JobsRepository(session)
        typer.echo(f"jobs_total={repository.count()}")
        typer.echo("dedupe_strategy=source_name+source_job_id with canonical fingerprints")


@jobs_app.command("deactivate-stale")
def jobs_deactivate_stale(
    days: int = typer.Option(30, "--days", min=1),
    source: str | None = typer.Option(None, "--source"),
    database_url: str | None = typer.Option(None, "--database-url"),
) -> None:
    """Deactivate jobs not seen within a window."""

    session_factory, _resolved_url = _session_factory(database_url)
    threshold = datetime.now(timezone.utc) - timedelta(days=days)
    with session_factory() as session:
        count = JobsRepository(session).deactivate_stale(source_name=source, seen_before=threshold)
        session.commit()
    typer.echo(f"jobs_deactivated={count}")


@runs_app.command("show")
def runs_show(
    database_url: str | None = typer.Option(None, "--database-url"),
) -> None:
    """Print recent crawl run summaries."""

    session_factory, _resolved_url = _session_factory(database_url)
    with session_factory() as session:
        runs = RunsRepository(session).list(limit=20)
        if not runs:
            typer.echo("no runs found")
            return
        for run in runs:
            typer.echo(
                f"run_id={run.id} status={run.status} adapters={run.adapter_scope} "
                f"seen={run.jobs_seen} created={run.jobs_created} errors={run.errors_count}"
            )


if __name__ == "__main__":
    app()
