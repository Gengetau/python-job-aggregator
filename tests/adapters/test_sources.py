import json
from pathlib import Path

from job_aggregator.app.adapters.custom_page import CustomPageAdapter, CustomPageConfig
from job_aggregator.app.adapters.greenhouse import GreenhouseAdapter
from job_aggregator.app.adapters.lever import LeverAdapter

FIXTURES = Path(__file__).parent / "fixtures"


def test_greenhouse_adapter_parses_fixture_json() -> None:
    payload = json.loads((FIXTURES / "greenhouse_jobs.json").read_text())
    adapter = GreenhouseAdapter()

    jobs = adapter.parse_payload(payload, company_name="Example")

    assert len(jobs) == 1
    assert jobs[0].source_job_id == "101"
    assert jobs[0].title == "Backend Engineer"
    assert jobs[0].company_name == "Example"
    assert jobs[0].location_text == "Remote"
    assert "Build Python APIs." in jobs[0].description_text


def test_lever_adapter_parses_fixture_json() -> None:
    payload = json.loads((FIXTURES / "lever_jobs.json").read_text())
    adapter = LeverAdapter()

    jobs = adapter.parse_payload(payload, company_name="Example")

    assert len(jobs) == 1
    assert jobs[0].source_job_id == "abc-123"
    assert jobs[0].title == "Data Platform Engineer"
    assert jobs[0].team_name == "Data"
    assert jobs[0].employment_type_text == "Full-time"


def test_custom_page_adapter_parses_fixture_html() -> None:
    html = (FIXTURES / "custom_jobs.html").read_text()
    config = CustomPageConfig(
        company_name="Example",
        listing_url="https://example.com/careers",
    )
    adapter = CustomPageAdapter()

    jobs = adapter.parse_html(html, config=config)

    assert len(jobs) == 1
    assert jobs[0].source_job_id == "custom-1"
    assert jobs[0].source_url == "https://example.com/careers/custom-1"
    assert jobs[0].title == "Product Engineer"
    assert jobs[0].location_text == "Hybrid / Tokyo"
