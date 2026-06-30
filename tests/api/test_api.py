import pytest
from fastapi.testclient import TestClient

from job_aggregator.app.adapters.demo import DemoAdapter
from job_aggregator.app.api.app import create_app
from job_aggregator.app.core.config import get_settings
from job_aggregator.app.db.models import Base
from job_aggregator.app.db.session import create_session_factory, make_engine


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


def test_create_app_initializes_configured_in_memory_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JOB_AGGREGATOR_DATABASE_URL", "sqlite:///:memory:")
    get_settings.cache_clear()
    app = create_app(adapters=[DemoAdapter()])
    client = TestClient(app)

    response = client.get("/jobs")

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
