# Python Job Aggregator

A Python-first showcase project for demonstrating engineering strength through a multi-source job crawler plus query API.

## Project Status

Design phase complete. Implementation planning is next.

## Repository Goals

- Multi-source job collection
- Adapter-driven crawler architecture
- Hybrid HTTP + browser fallback collection
- Normalization and deduplication pipeline
- Query API over structured job data
- Dockerized local development flow

## Current Contents

- `docs/specs/2026-06-30-python-job-aggregator-design.md`

## Planned Stack

- Python 3.12+
- FastAPI
- SQLAlchemy 2.x
- Alembic
- httpx
- Playwright
- Pydantic
- Typer
- pytest
- SQLite first, clean path to Postgres

## Next Step

Turn the approved design spec into an implementation plan, then scaffold the project in milestones.
