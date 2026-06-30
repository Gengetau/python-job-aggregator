from decimal import Decimal

from job_aggregator.app.adapters.base import RawJobPosting
from job_aggregator.app.pipeline.normalize import (
    canonical_fingerprint,
    classify_employment_type,
    classify_location_type,
    clean_title,
    normalize_job,
    parse_salary,
)


def raw_job(**overrides: object) -> RawJobPosting:
    values: dict[str, object] = {
        "source_name": "greenhouse",
        "source_job_id": "1",
        "source_url": "https://boards.example.com/jobs/1",
        "title": "Senior Python Engineer - Remote",
        "company_name": " Example Co ",
        "location_text": "Remote - US",
        "employment_type_text": "Full-time",
        "salary_text": "$120k - $150k",
        "description_text": "Build APIs with FastAPI and Python.",
        "tags": ["Backend"],
        "raw_payload": {"id": 1},
    }
    values.update(overrides)
    return RawJobPosting.model_validate(values)


def test_title_cleanup_removes_location_suffix() -> None:
    assert clean_title("Senior Engineer - Remote") == "Senior Engineer"


def test_location_type_classification() -> None:
    assert classify_location_type("Remote - United States") == "remote"
    assert classify_location_type("Hybrid / New York") == "hybrid"
    assert classify_location_type("Austin, Texas") == "onsite"
    assert classify_location_type("") == "unknown"


def test_employment_type_classification() -> None:
    assert classify_employment_type("Full-time") == "full_time"
    assert classify_employment_type("Part time") == "part_time"
    assert classify_employment_type("Internship") == "intern"
    assert classify_employment_type("Contractor") == "contract"


def test_salary_parsing_obvious_range() -> None:
    salary_min, salary_max, currency = parse_salary("$120k - $150k")

    assert salary_min == Decimal("120000")
    assert salary_max == Decimal("150000")
    assert currency == "USD"


def test_canonical_fingerprint_is_stable() -> None:
    first = canonical_fingerprint(
        title="Senior Engineer",
        company_name="Example Co",
        location_text="Remote",
        source_url="https://example.com/jobs/1",
    )
    second = canonical_fingerprint(
        title=" senior engineer ",
        company_name="example co",
        location_text=" remote ",
        source_url="https://example.com/jobs/2",
    )

    assert first == second


def test_normalize_job_generates_hash_and_tags() -> None:
    normalized = normalize_job(raw_job())

    assert normalized.title == "Senior Python Engineer"
    assert normalized.company_name == "Example Co"
    assert normalized.location_type == "remote"
    assert normalized.employment_type == "full_time"
    assert normalized.salary_currency == "USD"
    assert "python" in normalized.tags_json
    assert len(normalized.raw_hash) == 64
