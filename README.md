# Python Job Aggregator

A Python-first recruitment intelligence backend for collecting job postings from multiple sources, normalizing them into canonical records, deduplicating repeated listings, and exposing the result through a CLI and FastAPI API.

The project is intentionally backend-focused. It is designed to show a production-shaped crawler architecture without becoming a broad scraping framework or a frontend-heavy product.

## Current Status

This repository is in the foundation stage. The initial scaffold defines the package layout, configuration, logging, CLI placeholder, and test setup. Subsequent loops will add storage, adapters, fetchers, normalization, deduplication, the collector, and API routes.

## Planned Capabilities

- Adapter-driven job collection for sources such as Greenhouse, Lever, and configurable careers pages
- HTTP-first fetching with Playwright browser fallback infrastructure
- Deterministic normalization and conservative deduplication
- SQLite persistence with SQLAlchemy and Alembic migration support
- Crawl run tracking, checkpointing, and recoverable error records
- FastAPI query endpoints for jobs, sources, and crawl runs
- Typer CLI commands for local operators
- Dockerized local development flow

## Planned Stack

- Python 3.12+
- FastAPI
- SQLAlchemy 2.x
- Alembic
- SQLite for local persistence
- httpx
- Playwright
- Pydantic and pydantic-settings
- Typer and Rich
- pytest and pytest-asyncio

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
python -m pytest
```

On macOS or Linux, activate the virtual environment with:

```bash
source .venv/bin/activate
```

## Project Layout

```text
job_aggregator/
  app/
    api/
      routes/
      schemas/
    core/
    crawler/
    adapters/
    fetchers/
    pipeline/
    db/
      repositories/
    services/
    cli/
tests/
docs/
scripts/
docker/
```

## Design Source

The product and architecture source of truth for the current engineering loop is:

- `2026-06-30-python-job-aggregator-design.md`

The same design material is also kept under:

- `docs/specs/2026-06-30-python-job-aggregator-design.md`

## Development Principles

- Keep crawler adapters isolated behind one shared contract.
- Keep fetch infrastructure separate from extraction logic.
- Store normalized canonical jobs, not only raw scraped blobs.
- Avoid live websites in default tests; use fixtures for adapter behavior.
- Treat browser automation as a fallback for rendering support, not as the default path.

## Next Step

Continue with Loop 2: build the database foundation for canonical jobs, crawl runs, crawl errors, and source checkpoints.
