import sqlite3
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from uuid import uuid4

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from job_aggregator.app.cli.main import app
from job_aggregator.app.db.models import Base
from job_aggregator.app.db.repositories import (
    CheckpointsRepository,
    JobsRepository,
    RunsRepository,
)
from job_aggregator.app.db.session import (
    create_session_factory,
    init_database,
    make_engine,
    upgrade_database,
)


@pytest.fixture()
def session() -> Iterator[Session]:
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = create_session_factory(engine)
    with session_factory() as db_session:
        yield db_session


def job_values(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "canonical_fingerprint": "acme-software-engineer-remote",
        "source_name": "greenhouse",
        "source_job_id": "job-123",
        "source_url": "https://example.com/jobs/123",
        "title": "Software Engineer",
        "company_name": "Acme",
        "team_name": "Engineering",
        "location_text": "Remote",
        "location_type": "remote",
        "employment_type": "full_time",
        "description_text": "Build useful systems.",
        "tags_json": '["python"]',
        "raw_hash": "hash-v1",
    }
    values.update(overrides)
    return values


def shared_memory_database(prefix: str) -> tuple[str, sqlite3.Connection]:
    name = f"{prefix}_{uuid4().hex}"
    keeper = sqlite3.connect(f"file:{name}?mode=memory&cache=shared", uri=True)
    url = f"sqlite:///file:{name}?mode=memory&cache=shared&uri=true"
    return url, keeper


def serve_html(html: str) -> tuple[ThreadingHTTPServer, str]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            encoded = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    return server, f"http://{host}:{port}/careers"


def test_init_database_creates_core_tables() -> None:
    engine = init_database("sqlite:///:memory:")

    table_names = set(inspect(engine).get_table_names())

    assert {
        "jobs",
        "crawl_runs",
        "crawl_run_adapter_states",
        "crawl_run_errors",
        "source_checkpoints",
    }.issubset(table_names)


def test_upgrade_database_applies_alembic_schema() -> None:
    database_url, keeper = shared_memory_database("migrated")

    try:
        upgrade_database(database_url)
        engine = make_engine(database_url)
        table_names = set(inspect(engine).get_table_names())
    finally:
        keeper.close()

    assert "alembic_version" in table_names
    assert {"jobs", "crawl_runs", "crawl_run_adapter_states", "source_checkpoints"}.issubset(
        table_names
    )


def test_jobs_repository_creates_and_queries_job(session: Session) -> None:
    repository = JobsRepository(session)

    created = repository.create(**job_values())
    session.commit()

    loaded = repository.get(created.id)

    assert loaded is not None
    assert loaded.title == "Software Engineer"
    assert loaded.source_name == "greenhouse"
    assert repository.count() == 1
    assert repository.get_by_source_identity("greenhouse", "job-123") == loaded


def test_jobs_repository_upserts_same_source_identity(session: Session) -> None:
    repository = JobsRepository(session)

    created, created_status = repository.upsert_by_source_identity(job_values())
    updated, updated_status = repository.upsert_by_source_identity(
        job_values(title="Senior Software Engineer", raw_hash="hash-v2"),
    )
    session.commit()

    assert created_status == "created"
    assert updated_status == "updated"
    assert updated.id == created.id
    assert repository.count() == 1
    assert updated.title == "Senior Software Engineer"


def test_runs_repository_tracks_errors_and_summary(session: Session) -> None:
    repository = RunsRepository(session)

    run = repository.create_run(trigger_type="manual", adapter_scope="greenhouse")
    error = repository.record_error(
        run,
        adapter_name="greenhouse",
        stage="fetch",
        target_url="https://example.com/jobs",
        error_type="FetchError",
        message="Request timed out",
    )
    repository.finish_run(
        run,
        status="partial_success",
        jobs_seen=3,
        jobs_created=2,
        jobs_updated=1,
    )
    session.commit()

    loaded = repository.get(run.id)

    assert loaded is not None
    assert loaded.status == "partial_success"
    assert loaded.errors_count == 1
    assert loaded.jobs_seen == 3
    assert error.run_id == run.id


def test_runs_repository_tracks_adapter_state(session: Session) -> None:
    repository = RunsRepository(session)
    run = repository.create_run(trigger_type="manual", adapter_scope="demo")

    state = repository.create_adapter_state(
        run,
        adapter_name="demo",
        scope_key="fixture",
        checkpoint_before="before",
    )
    repository.finish_adapter_state(state, checkpoint_after="after")
    session.commit()

    states = repository.list_adapter_states(run.id)

    assert len(states) == 1
    assert states[0].adapter_name == "demo"
    assert states[0].scope_key == "fixture"
    assert states[0].checkpoint_before == "before"
    assert states[0].checkpoint_after == "after"


def test_checkpoints_repository_upserts_cursor(session: Session) -> None:
    repository = CheckpointsRepository(session)

    first = repository.upsert(
        adapter_name="lever",
        scope_key="acme",
        cursor_value="page-1",
    )
    second = repository.upsert(
        adapter_name="lever",
        scope_key="acme",
        cursor_value="page-2",
    )
    session.commit()

    assert first.id == second.id
    assert repository.get("lever", "acme").cursor_value == "page-2"  # type: ignore[union-attr]
    assert repository.latest_for_adapter("lever").cursor_value == "page-2"  # type: ignore[union-attr]


def test_jobs_repository_returns_cross_source_duplicate_candidates(session: Session) -> None:
    repository = JobsRepository(session)
    repository.create(**job_values())
    repository.create(
        **job_values(
            source_name="lever",
            source_job_id="job-456",
            source_url="https://lever.example.com/jobs/456",
            raw_hash="hash-v2",
        )
    )
    repository.create(
        **job_values(
            source_name="greenhouse",
            source_job_id="job-789",
            source_url="https://example.com/jobs/789",
            title="Product Engineer",
            raw_hash="hash-v3",
        )
    )
    session.commit()

    candidates = repository.duplicate_candidates()

    assert len(candidates) == 1
    assert candidates[0].confidence == 0.95
    assert "same normalized title" in candidates[0].reason
    assert {job.source_name for job in candidates[0].jobs} == {"greenhouse", "lever"}


def test_cli_db_init_command() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["db", "init", "--database-url", "sqlite:///:memory:"])

    assert result.exit_code == 0
    assert "applied migrations" in result.output


def test_cli_crawl_run_demo_command() -> None:
    runner = CliRunner()
    database_url, keeper = shared_memory_database("cli_demo")

    try:
        result = runner.invoke(
            app,
            ["crawl", "run", "--database-url", database_url],
        )
    finally:
        keeper.close()

    assert result.exit_code == 0
    assert "running_adapters=demo" in result.output
    assert "status=success" in result.output
    assert "jobs_created=2" in result.output


def test_cli_crawl_run_all_reports_explicit_adapter_set() -> None:
    runner = CliRunner()
    database_url, keeper = shared_memory_database("cli_all")

    try:
        result = runner.invoke(
            app,
            ["crawl", "run", "--all", "--database-url", database_url],
        )
    finally:
        keeper.close()

    assert result.exit_code == 0
    assert "running_adapters=demo" in result.output


def test_cli_crawl_resume_uses_previous_run_scope_and_checkpoint() -> None:
    runner = CliRunner()
    database_url, keeper = shared_memory_database("resume")

    try:
        run_result = runner.invoke(app, ["crawl", "run", "--database-url", database_url])
        engine = make_engine(database_url)
        session_factory = create_session_factory(engine)
        with session_factory() as session:
            CheckpointsRepository(session).upsert(
                adapter_name="demo",
                scope_key="fixture",
                cursor_value="newer-global-checkpoint",
            )
            session.commit()
        resume_result = runner.invoke(
            app,
            ["crawl", "resume", "--run-id", "1", "--database-url", database_url],
        )
        with session_factory() as session:
            resumed_states = RunsRepository(session).list_adapter_states(2)
    finally:
        keeper.close()

    assert run_result.exit_code == 0
    assert resume_result.exit_code == 0
    assert "resuming_from_run_id=1" in resume_result.output
    assert "resuming_adapters=demo" in resume_result.output
    assert (
        "resume_context adapter=demo scope_key=fixture checkpoint=demo-complete"
        in resume_result.output
    )
    assert "running_adapters=demo" in resume_result.output
    assert len(resumed_states) == 1
    assert resumed_states[0].checkpoint_before == "demo-complete"
    assert resumed_states[0].checkpoint_after == "demo-complete"


def test_cli_jobs_dedupe_outputs_candidate_groups() -> None:
    runner = CliRunner()
    database_url, keeper = shared_memory_database("dedupe")

    try:
        upgrade_database(database_url)
        engine = make_engine(database_url)
        session_factory = create_session_factory(engine)
        with session_factory() as session:
            repository = JobsRepository(session)
            repository.create(**job_values())
            repository.create(
                **job_values(
                    source_name="lever",
                    source_job_id="job-456",
                    source_url="https://lever.example.com/jobs/456",
                    is_active=False,
                    raw_hash="hash-v2",
                )
            )
            session.commit()

        active_result = runner.invoke(app, ["jobs", "dedupe", "--database-url", database_url])
        inactive_result = runner.invoke(
            app,
            [
                "jobs",
                "dedupe",
                "--include-inactive",
                "--limit",
                "1",
                "--scanned-limit",
                "10",
                "--database-url",
                database_url,
            ],
        )
    finally:
        keeper.close()

    assert active_result.exit_code == 0
    assert "include_inactive=False" in active_result.output
    assert "candidate_groups=0" in active_result.output
    assert inactive_result.exit_code == 0
    assert "include_inactive=True" in inactive_result.output
    assert "candidate_groups=1" in inactive_result.output
    assert "confidence=0.95" in inactive_result.output


def test_cli_crawl_run_custom_page_listing_url() -> None:
    runner = CliRunner()
    database_url, keeper = shared_memory_database("custom_page")
    html = """
    <article class="job" data-id="custom-1">
      <a class="title" href="/careers/custom-1">Product Engineer</a>
      <span class="location">Remote</span>
    </article>
    """
    server, listing_url = serve_html(html)

    try:
        result = runner.invoke(
            app,
            [
                "crawl",
                "run",
                "--adapter",
                "custom_page",
                "--listing-url",
                listing_url,
                "--company",
                "Example",
                "--database-url",
                database_url,
            ],
        )
    finally:
        server.shutdown()
        server.server_close()
        keeper.close()

    assert result.exit_code == 0
    assert "running_adapters=custom_page" in result.output
    assert "jobs_created=1" in result.output
