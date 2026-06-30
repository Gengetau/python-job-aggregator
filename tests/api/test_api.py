import sqlite3
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from job_aggregator.app.adapters.demo import DemoAdapter
from job_aggregator.app.api.app import create_app
from job_aggregator.app.core.config import get_settings
from job_aggregator.app.db.models import Base
from job_aggregator.app.db.repositories.jobs import JobsRepository
from job_aggregator.app.db.session import create_session_factory, make_engine
from tests.adapters.fakes import FakeJobAdapter


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


@pytest.fixture()
def client() -> TestClient:
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    app = create_app(
        session_factory=create_session_factory(engine),
        adapters=[DemoAdapter()],
    )
    return TestClient(app)


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_schema_is_generated(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/jobs" in response.json()["paths"]


def test_create_app_initializes_configured_in_memory_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url, keeper = shared_memory_database("api_app")
    try:
        monkeypatch.setenv("JOB_AGGREGATOR_DATABASE_URL", database_url)
        get_settings.cache_clear()
        app = create_app(adapters=[DemoAdapter()])
        client = TestClient(app)

        response = client.get("/jobs")
    finally:
        keeper.close()

    assert response.status_code == 200
    assert response.json()["total"] == 0
    get_settings.cache_clear()


def test_admin_crawl_populates_jobs_and_runs(client: TestClient) -> None:
    crawl_response = client.post("/admin/crawl", json={"adapters": ["demo"]})

    assert crawl_response.status_code == 200
    assert crawl_response.json()["status"] == "success"
    assert crawl_response.json()["jobs_created"] == 2

    jobs_response = client.get("/jobs", params={"q": "python", "page_size": 10})
    assert jobs_response.status_code == 200
    jobs_payload = jobs_response.json()
    assert jobs_payload["total"] == 1
    assert jobs_payload["items"][0]["company_name"] == "Acme Analytics"

    job_id = jobs_payload["items"][0]["id"]
    assert client.get(f"/jobs/{job_id}").status_code == 200

    sources_response = client.get("/sources")
    assert sources_response.status_code == 200
    assert sources_response.json()[0]["source_name"] == "demo"

    runs_response = client.get("/runs")
    assert runs_response.status_code == 200
    assert runs_response.json()[0]["jobs_seen"] == 2

    run_id = crawl_response.json()["run_id"]
    assert client.get(f"/runs/{run_id}").status_code == 200


def test_admin_crawl_passes_adapter_options_to_context() -> None:
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    adapter = FakeJobAdapter()
    app = create_app(
        session_factory=create_session_factory(engine),
        adapters=[adapter],
    )
    client = TestClient(app)

    response = client.post(
        "/admin/crawl",
        json={
            "adapters": ["fake"],
            "options": {
                "fake": {
                    "scope_key": "board-a",
                    "company_name": "Acme",
                }
            },
        },
    )

    assert response.status_code == 200
    assert adapter.seen_context is not None
    assert adapter.seen_context.scope_key == "board-a"
    assert adapter.seen_context.options == {"company_name": "Acme"}


def test_dedupe_candidates_endpoint_returns_cross_source_groups() -> None:
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
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
    app = create_app(
        session_factory=session_factory,
        adapters=[DemoAdapter()],
    )
    client = TestClient(app)

    response = client.get("/dedupe/candidates")
    inactive_response = client.get("/dedupe/candidates", params={"include_inactive": True})

    assert response.status_code == 200
    assert response.json() == []
    assert inactive_response.status_code == 200
    payload = inactive_response.json()
    assert len(payload) == 1
    assert payload[0]["confidence"] == 0.95
    assert {job["source_name"] for job in payload[0]["jobs"]} == {"greenhouse", "lever"}


def test_jobs_filters_and_pagination(client: TestClient) -> None:
    client.post("/admin/crawl", json={"adapters": ["demo"]})

    response = client.get(
        "/jobs",
        params={
            "location_type": "hybrid",
            "employment_type": "full_time",
            "page": 1,
            "page_size": 1,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["title"] == "Data Platform Engineer"
