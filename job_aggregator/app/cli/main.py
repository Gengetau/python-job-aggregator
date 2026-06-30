"""Typer command line entrypoint."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import typer

from job_aggregator import __version__
from job_aggregator.app.adapters import (
    CustomPageAdapter,
    CustomPageConfig,
    DemoAdapter,
    GreenhouseAdapter,
    LeverAdapter,
)
from job_aggregator.app.adapters.base import AdapterContext, BaseJobAdapter
from job_aggregator.app.core.config import get_settings
from job_aggregator.app.core.logging import configure_logging
from job_aggregator.app.crawler.collector import Collector
from job_aggregator.app.crawler.contexts import context_from_options
from job_aggregator.app.db.repositories.jobs import JobsRepository
from job_aggregator.app.db.repositories.runs import RunsRepository
from job_aggregator.app.db.session import create_session_factory, make_engine, upgrade_database

app = typer.Typer(help="Operate the Python Job Aggregator service.")
db_app = typer.Typer(help="Manage local database schema.")
crawl_app = typer.Typer(help="Run and resume crawl operations.")
jobs_app = typer.Typer(help="Maintain stored jobs.")
runs_app = typer.Typer(help="Inspect crawl runs.")
app.add_typer(db_app, name="db")
app.add_typer(crawl_app, name="crawl")
app.add_typer(jobs_app, name="jobs")
app.add_typer(runs_app, name="runs")

LOCAL_ALL_ADAPTER_NAMES = ("demo",)


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
    upgrade_database(resolved_url)
    engine = make_engine(resolved_url)
    return create_session_factory(engine), resolved_url


def _adapter_for(adapter_name: str | None) -> BaseJobAdapter:
    name = (adapter_name or "demo").lower()
    if name == "demo":
        return DemoAdapter()
    if name == "greenhouse":
        return GreenhouseAdapter()
    if name == "lever":
        return LeverAdapter()
    if name == "custom_page":
        return CustomPageAdapter()
    raise typer.BadParameter(f"Unknown adapter: {adapter_name}")


def _adapter_names_from_scope(adapter_scope: str) -> list[str]:
    return [
        adapter_name.strip()
        for adapter_name in adapter_scope.split(",")
        if adapter_name.strip() and adapter_name.strip() != "none"
    ]


def _cli_context(
    adapter_name: str,
    *,
    scope: str | None,
    company: str | None,
    api_url: str | None,
    config_file: Path | None,
    listing_url: str | None,
) -> AdapterContext | None:
    options: dict[str, Any] = {}
    if adapter_name == "custom_page":
        options.update(
            _custom_page_options(
                config_file=config_file,
                listing_url=listing_url,
                company=company,
            )
        )
    if scope:
        if adapter_name == "greenhouse":
            options["board_token"] = scope
        elif adapter_name == "lever":
            options["company_slug"] = scope
        else:
            options["scope_key"] = scope
    if company:
        options["company_name"] = company
    if api_url:
        options["api_url"] = api_url
    return context_from_options(options) if options else None


def _custom_page_options(
    *,
    config_file: Path | None,
    listing_url: str | None,
    company: str | None,
) -> dict[str, Any]:
    if config_file is not None:
        try:
            values = json.loads(config_file.read_text(encoding="utf-8"))
            config = CustomPageConfig.model_validate(values)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise typer.BadParameter(f"Invalid custom page config file: {exc}") from exc
        config_values = config.model_dump()
        if company:
            config_values["company_name"] = company
        return config_values

    if listing_url:
        if not company:
            raise typer.BadParameter("--company is required when --listing-url is used.")
        return CustomPageConfig(company_name=company, listing_url=listing_url).model_dump()

    raise typer.BadParameter("custom_page requires --config-file or --listing-url.")


def _resume_contexts(run_id: int, database_url: str | None) -> dict[str, AdapterContext]:
    session_factory, _resolved_url = _session_factory(database_url)
    contexts: dict[str, AdapterContext] = {}
    with session_factory() as session:
        states = RunsRepository(session).list_adapter_states(run_id)
        for state in states:
            contexts[state.adapter_name] = AdapterContext(
                scope_key=state.scope_key,
                checkpoint=state.checkpoint_after,
            )
    return contexts


def _format_adapter_names(adapters: list[BaseJobAdapter]) -> str:
    return ",".join(adapter.name for adapter in adapters) or "none"


async def _run_collector(
    *,
    adapters: list[BaseJobAdapter],
    database_url: str | None = None,
    trigger_type: str = "manual",
    contexts: Mapping[str, AdapterContext] | None = None,
    checkpoint_source: str = "latest",
) -> None:
    session_factory, resolved_url = _session_factory(database_url)
    result = await Collector(adapters=adapters, session_factory=session_factory).run(
        trigger_type=trigger_type,
        contexts=contexts,
        checkpoint_source=checkpoint_source,
    )
    typer.echo(f"database_url={resolved_url}")
    typer.echo(f"running_adapters={_format_adapter_names(adapters)}")
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
    """Apply database migrations for local development."""

    settings = get_settings()
    resolved_url = database_url or settings.database_url
    upgrade_database(resolved_url)
    typer.echo(f"applied migrations: {resolved_url}")


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
        help="Run all locally configured adapters. This is demo by default.",
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
    config_file: Path | None = typer.Option(
        None,
        "--config-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="JSON CustomPageConfig file for the custom_page adapter.",
    ),
    listing_url: str | None = typer.Option(
        None,
        "--listing-url",
        help="Careers page URL for the custom_page adapter using default selectors.",
    ),
    database_url: str | None = typer.Option(None, "--database-url"),
) -> None:
    """Run a crawl."""

    adapter_names = list(LOCAL_ALL_ADAPTER_NAMES) if all_adapters else [adapter or "demo"]
    adapters = [_adapter_for(adapter_name) for adapter_name in adapter_names]
    contexts: dict[str, AdapterContext] = {}
    for adapter_instance in adapters:
        context = _cli_context(
            adapter_instance.name,
            scope=scope,
            company=company,
            api_url=api_url,
            config_file=config_file,
            listing_url=listing_url,
        )
        if context is not None:
            contexts[adapter_instance.name] = context
    asyncio.run(
        _run_collector(
            adapters=adapters,
            database_url=database_url,
            contexts=contexts,
        )
    )


@crawl_app.command("resume")
def crawl_resume(
    run_id: int = typer.Option(
        ...,
        "--run-id",
        help="Run id whose checkpoint context should be resumed.",
    ),
    database_url: str | None = typer.Option(None, "--database-url"),
) -> None:
    """Resume from stored checkpoints using the adapters from a previous run."""

    session_factory, _resolved_url = _session_factory(database_url)
    with session_factory() as session:
        run = RunsRepository(session).get(run_id)
        if run is None:
            raise typer.BadParameter(f"No crawl run found for run_id={run_id}")
        states = RunsRepository(session).list_adapter_states(run_id)
        adapter_names = [state.adapter_name for state in states]

    if not adapter_names:
        raise typer.BadParameter(f"Run {run_id} has no adapter state to resume.")

    adapters = [_adapter_for(adapter_name) for adapter_name in adapter_names]
    contexts = _resume_contexts(run_id, database_url)
    typer.echo(f"resuming_from_run_id={run_id}")
    typer.echo(f"resuming_adapters={_format_adapter_names(adapters)}")
    for adapter_name, context in contexts.items():
        checkpoint = context.checkpoint or "<none>"
        typer.echo(
            f"resume_context adapter={adapter_name} "
            f"scope_key={context.scope_key} checkpoint={checkpoint}"
        )
    asyncio.run(
        _run_collector(
            adapters=adapters,
            database_url=database_url,
            trigger_type="manual",
            contexts=contexts,
            checkpoint_source="context",
        )
    )


@jobs_app.command("dedupe")
def jobs_dedupe(
    limit: int = typer.Option(50, "--limit", min=1, max=100),
    scanned_limit: int = typer.Option(1000, "--scanned-limit", min=1, max=5000),
    include_inactive: bool = typer.Option(
        False,
        "--include-inactive",
        help="Include inactive jobs in duplicate candidate review.",
    ),
    database_url: str | None = typer.Option(None, "--database-url"),
) -> None:
    """Show conservative cross-source dedupe candidates."""

    session_factory, _resolved_url = _session_factory(database_url)
    with session_factory() as session:
        repository = JobsRepository(session)
        candidates = repository.duplicate_candidates(
            limit=limit,
            scanned_limit=scanned_limit,
            active_only=not include_inactive,
        )
        typer.echo(f"jobs_total={repository.count()}")
        typer.echo(f"include_inactive={include_inactive}")
        typer.echo(f"candidate_groups={len(candidates)}")
        for index, candidate in enumerate(candidates, start=1):
            typer.echo(
                f"group={index} fingerprint={candidate.fingerprint} "
                f"confidence={candidate.confidence:.2f} reason={candidate.reason}"
            )
            for job in candidate.jobs:
                typer.echo(
                    f"  job_id={job.id} source={job.source_name} "
                    f"source_job_id={job.source_job_id} title={job.title!r} "
                    f"company={job.company_name!r}"
                )


@jobs_app.command("deactivate-stale")
def jobs_deactivate_stale(
    days: int = typer.Option(30, "--days", min=1),
    source: str | None = typer.Option(None, "--source"),
    database_url: str | None = typer.Option(None, "--database-url"),
) -> None:
    """Deactivate jobs not seen within a window."""

    session_factory, _resolved_url = _session_factory(database_url)
    threshold = datetime.now(UTC) - timedelta(days=days)
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
