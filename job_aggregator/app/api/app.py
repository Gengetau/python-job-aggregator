"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import Iterable

from fastapi import FastAPI
from sqlalchemy.orm import Session, sessionmaker

from job_aggregator.app.adapters.base import BaseJobAdapter
from job_aggregator.app.adapters.custom_page import CustomPageAdapter
from job_aggregator.app.adapters.demo import DemoAdapter
from job_aggregator.app.adapters.greenhouse import GreenhouseAdapter
from job_aggregator.app.adapters.lever import LeverAdapter
from job_aggregator.app.api.routes import admin, dedupe, health, jobs, runs, sources
from job_aggregator.app.core.config import get_settings
from job_aggregator.app.db.session import create_session_factory, make_engine, upgrade_database


def create_app(
    *,
    session_factory: sessionmaker[Session] | None = None,
    adapters: Iterable[BaseJobAdapter] | None = None,
) -> FastAPI:
    """Create and configure the API application."""

    app = FastAPI(
        title="Python Job Aggregator",
        version="0.1.0",
        description="Recruitment intelligence API for collected and normalized jobs.",
    )

    if session_factory is None:
        database_url = get_settings().database_url
        upgrade_database(database_url)
        engine = make_engine(database_url)
        session_factory = create_session_factory(engine)

    app.state.session_factory = session_factory
    app.state.adapters = (
        list(adapters)
        if adapters is not None
        else [DemoAdapter(), GreenhouseAdapter(), LeverAdapter(), CustomPageAdapter()]
    )

    app.include_router(health.router)
    app.include_router(jobs.router)
    app.include_router(dedupe.router)
    app.include_router(sources.router)
    app.include_router(runs.router)
    app.include_router(admin.router)
    return app
