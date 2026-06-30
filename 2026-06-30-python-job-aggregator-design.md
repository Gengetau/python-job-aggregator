# Python Job Aggregator Design

Date: 2026-06-30
Owner: Luna
Status: Draft for user review

## Goal

Build a medium-sized Python showcase project that demonstrates real engineering strength through a multi-source job crawler plus query API.

The project should feel like a deployable internal platform, not a one-off script. It must show:

- adapter-driven crawler architecture
- hybrid HTTP and browser automation collection
- normalization and deduplication pipeline
- structured persistence and query API
- operational concerns like retries, throttling, checkpoints, and run summaries

## Why This Project

The user wants a repository that can "show off" technical ability.

A plain crawler script is too small and too easy to dismiss.
A full frontend-heavy product would dilute the core signal.

The strongest middle ground is:

- clearly Python-first
- obviously useful in the real world
- technically richer than CRUD
- broad enough to show architecture skill
- narrow enough to finish as a coherent showcase

## Product Shape

This project is a job aggregation backend focused on collecting roles from multiple recruitment sources and exposing a clean query surface.

It is not a generic web scraping framework for everything.
It is not a full job board product.
It is not a data science notebook collection.

It is a focused recruitment-intelligence service with strong internal structure.

## Scope

### In Scope

- multi-site job collection
- plugin-like source adapters
- hybrid fetch strategy: direct HTTP first, browser fallback when needed
- normalized canonical job model
- deduplication across sources
- SQLite-first storage with clean migration path to Postgres
- FastAPI-based query API
- crawl runs, error tracking, and refresh summaries
- local CLI entrypoints for crawl and maintenance operations
- Dockerized development and run path
- OpenAPI-ready API docs

### Out of Scope

- account system
- resume upload
- recommendation engine
- embeddings / semantic ranking in v1
- public polished frontend
- message push / email alerts in v1
- distributed queue / worker cluster
- broad anti-bot warfare against the hardest consumer platforms

## Showcase Priorities

This project should optimize for visible engineering quality.

The strongest showcase signals are:

1. Clear architecture with crisp module boundaries
2. Adapter abstraction that makes new sources cheap to add
3. Thoughtful data normalization instead of raw dump scraping
4. Operational discipline: retries, rate limits, checkpoints, run records
5. A useful API surface on top of collected data

This means the codebase should prefer clarity and system design over gimmicks.

## Initial Source Strategy

The first version should target 2-3 sources that are realistic, respectable, and structurally tractable:

1. Greenhouse-hosted job boards
2. Lever-hosted job boards
3. A configurable "custom company careers page" adapter for simpler ATS-like pages or structured listing pages

Reasoning:

- Greenhouse and Lever are recognizable enough to feel real
- they provide strong showcase value without forcing the project into the ugliest scraping trench immediately
- they create a natural adapter pattern because the core entity is the same while extraction details differ

The system should be designed so that future adapters can be added for:

- Ashby
- Workday-derived pages
- BambooHR
- company-specific custom sites

## High-Level Architecture

The system should be split into these main layers:

### 1. Collector Layer

Responsible for orchestrating crawl runs.

Responsibilities:

- choose target adapters and crawl scope
- manage concurrency and throttling
- persist run lifecycle state
- dispatch raw records into normalization
- capture source-specific failures without taking down the whole run

### 2. Adapter Layer

Each source has its own adapter.

Responsibilities:

- know how to enumerate jobs from that source
- fetch listing and detail data
- convert source responses into a shared raw intermediate shape
- declare whether the adapter uses HTTP only, browser only, or hybrid mode

Each adapter must implement the same interface so the collector can treat adapters uniformly.

### 3. Fetch Engine Layer

Shared infrastructure for site access.

Responsibilities:

- HTTP client management
- browser automation fallback
- retries, timeouts, backoff
- optional caching / checkpointing
- per-host rate limiting

This layer is infrastructure only. It should not contain job extraction logic.

### 4. Normalization Pipeline

Transforms source-specific raw job data into canonical job entities.

Responsibilities:

- title cleanup
- company normalization
- location parsing
- salary parsing when possible
- tag extraction
- remote / hybrid / onsite classification
- source fingerprint generation

### 5. Deduplication Layer

Handles duplicate jobs across sources and repeated crawls.

Responsibilities:

- stable job fingerprinting
- same-source update detection
- cross-source duplicate candidate detection
- soft merge rules for equivalent records

### 6. Storage Layer

Responsible for persistence and repository logic.

Responsibilities:

- schema definition
- CRUD and query composition
- crawl run history
- adapter metadata storage
- dedup state and raw snapshot references

### 7. API Layer

Exposes collected data for downstream use.

Responsibilities:

- filterable job listing endpoints
- source and run summary endpoints
- health and readiness endpoints
- crawl trigger endpoints for local/admin use

## Recommended Stack

Use a modern but disciplined Python stack:

- Python 3.12+
- FastAPI for API
- SQLAlchemy 2.x for ORM / DB access
- Alembic for migrations
- SQLite for v1 local persistence
- httpx for HTTP fetching
- Playwright for browser fallback
- Pydantic for request/response and internal schemas
- Typer for CLI
- pytest for tests
- Docker / docker-compose for local environment

Why this stack:

- modern and respected
- readable to recruiters and engineers
- strong ecosystem
- good fit for crawler + API hybrid service

## Project Structure

Suggested structure:

```text
job_aggregator/
  app/
    api/
      routes/
      schemas/
    core/
      config.py
      logging.py
    crawler/
      collector.py
      scheduler.py
      checkpoints.py
    adapters/
      base.py
      greenhouse.py
      lever.py
      custom_page.py
    fetchers/
      http.py
      browser.py
      rate_limit.py
    pipeline/
      normalize.py
      dedupe.py
      enrich.py
    db/
      models.py
      session.py
      repositories/
      migrations/
    services/
      jobs.py
      runs.py
    cli/
      main.py
  tests/
    adapters/
    api/
    pipeline/
    integration/
  scripts/
  docker/
  docs/
```

## Core Data Model

The canonical job entity should be the center of the system.

### Job

Fields:

- `id`
- `canonical_fingerprint`
- `source_name`
- `source_job_id`
- `source_url`
- `title`
- `company_name`
- `team_name`
- `location_text`
- `location_type` (`onsite|hybrid|remote|unknown`)
- `employment_type` (`full_time|part_time|contract|intern|unknown`)
- `salary_min`
- `salary_max`
- `salary_currency`
- `description_text`
- `tags_json`
- `posted_at`
- `scraped_at`
- `last_seen_at`
- `is_active`
- `raw_hash`

### CrawlRun

Fields:

- `id`
- `started_at`
- `finished_at`
- `status`
- `trigger_type` (`manual|scheduled|api`)
- `adapter_scope`
- `jobs_seen`
- `jobs_created`
- `jobs_updated`
- `jobs_deactivated`
- `errors_count`

### CrawlRunError

Fields:

- `id`
- `run_id`
- `adapter_name`
- `stage`
- `target_url`
- `error_type`
- `message`
- `created_at`

### SourceCheckpoint

Fields:

- `id`
- `adapter_name`
- `scope_key`
- `cursor_value`
- `updated_at`

## Deduplication Design

The project should not rely on naive URL-only deduplication.

Use two layers:

### Hard Identity

For same-source updates:

- `source_name + source_job_id`

This identifies the same listing across crawls.

### Soft Canonical Identity

For possible cross-source duplicates:

- normalized title
- normalized company
- normalized location
- optional source URL family

Generate a canonical fingerprint from those fields.

Soft dedup should be conservative in v1:

- merge only when confidence is high
- avoid clever fuzzy logic that can silently corrupt data

## Fetch Strategy

Use hybrid acquisition:

### HTTP-first

Default path for:

- APIs
- static listing pages
- JSON embedded in page payloads

Benefits:

- faster
- cheaper
- easier to test

### Browser fallback

Use Playwright only when needed:

- client-rendered job lists
- lazy-loaded details
- script-generated payloads
- anti-bot behavior that still allows headless access

The adapter should declare its preferred mode, but the collector may allow fallback when HTTP parsing fails.

## Reliability Design

The crawler should visibly behave like a real system, not a fragile demo.

Required reliability features:

- per-request timeout
- bounded retries with exponential backoff
- host-level concurrency caps
- run-level error aggregation
- adapter isolation
- checkpoint support for resumable listing traversal
- structured logging

If one adapter fails, the run should finish with partial success and expose clear failure records.

## API Design

The API should emphasize clean querying over surface-area bloat.

### Core Endpoints

- `GET /health`
- `GET /jobs`
- `GET /jobs/{job_id}`
- `GET /sources`
- `GET /runs`
- `GET /runs/{run_id}`
- `POST /admin/crawl`

### `GET /jobs` filters

- `q`
- `company`
- `source`
- `location`
- `location_type`
- `employment_type`
- `posted_after`
- `is_active`
- `page`
- `page_size`
- `sort`

### Summary endpoints

Potential lightweight aggregated views:

- jobs by source
- jobs by company
- jobs by location type
- latest crawl freshness

## CLI Design

The CLI is part of the showcase and should feel intentional.

Commands:

- `crawl run --adapter greenhouse`
- `crawl run --all`
- `crawl resume --run-id ...`
- `jobs dedupe`
- `jobs deactivate-stale`
- `runs show`
- `db init`

This makes the repo look like a usable operator tool, not just a library.

## Testing Strategy

The test story needs to be credible.

### Unit Tests

- adapter parsing on captured fixtures
- normalization rules
- salary parsing
- fingerprint generation
- dedup rules

### API Tests

- job listing filters
- pagination
- run summary responses

### Integration Tests

- full crawl against stored HTML/JSON fixtures
- repository writes
- end-to-end crawl run state transitions

Avoid using live websites in default tests.
Live sources are unstable and make the project look sloppy.

## Local Developer Experience

The project should include:

- `.env.example`
- `Makefile` or clear CLI tasks
- Docker compose for API + DB
- easy startup path
- seeded example data or fixture-powered demo mode

A reviewer should be able to run the project locally without reverse-engineering your repo.

## Security and Ethics

This project should avoid looking reckless.

Guardrails:

- respect bounded request rates
- do not include credential theft or bypass logic
- do not claim universal anti-bot defeat
- keep browser fallback as legitimate rendering support, not exploit theatre

The point is to show engineering strength, not irresponsible scraping behavior.

## Initial Milestones

### Milestone 1

Foundation:

- project scaffolding
- config
- DB schema
- canonical models
- CLI skeleton

### Milestone 2

Crawler core:

- collector
- fetch engines
- base adapter contract
- run tracking

### Milestone 3

First real sources:

- Greenhouse adapter
- Lever adapter
- normalization + dedup pipeline

### Milestone 4

API surface:

- job query endpoints
- run summary endpoints
- admin crawl trigger

### Milestone 5

Showcase polish:

- Docker setup
- OpenAPI polish
- fixture tests
- sample report artifacts
- README with architecture diagram and examples

## Recommendation

Build this as a plugin-oriented crawler service with a query API, not as a Scrapy-centric monolith and not as a frontend-heavy product.

That path best satisfies the user's real goal:

- looks serious
- feels architectural
- stays Python-first
- demonstrates both low-level scraping skill and higher-level system design

## Success Criteria

This project succeeds if a reviewer can quickly see:

1. the repo has clean architecture
2. the crawler can support multiple sites through adapters
3. the system handles real-world collection concerns
4. the stored data is normalized and queryable
5. the project feels expandable into a real product

This project fails if it looks like:

- a single giant script
- a toy CRUD app with incidental scraping
- a framework cosplay repo with no concrete output
- a frontend shell hiding weak crawler internals
