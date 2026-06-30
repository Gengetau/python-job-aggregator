"""Typer command line entrypoint."""

import typer

from job_aggregator import __version__
from job_aggregator.app.core.config import get_settings
from job_aggregator.app.core.logging import configure_logging

app = typer.Typer(help="Operate the Python Job Aggregator service.")


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
