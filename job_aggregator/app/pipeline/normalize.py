"""Deterministic normalization from raw adapter records to canonical jobs."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict

from job_aggregator.app.adapters.base import RawJobPosting

LOCATION_TYPES = {"onsite", "hybrid", "remote", "unknown"}
EMPLOYMENT_TYPES = {"full_time", "part_time", "contract", "intern", "unknown"}


class CanonicalJobData(BaseModel):
    """Normalized job payload ready for repository persistence."""

    canonical_fingerprint: str
    source_name: str
    source_job_id: str
    source_url: str
    title: str
    company_name: str
    team_name: str | None = None
    location_text: str | None = None
    location_type: str = "unknown"
    employment_type: str = "unknown"
    salary_min: Decimal | None = None
    salary_max: Decimal | None = None
    salary_currency: str | None = None
    description_text: str | None = None
    tags_json: str = "[]"
    posted_at: datetime | None = None
    scraped_at: datetime
    last_seen_at: datetime
    is_active: bool = True
    raw_hash: str

    model_config = ConfigDict(extra="forbid")

    def to_repository_values(self) -> dict[str, Any]:
        """Return a dict suitable for JobsRepository upsert operations."""

        return self.model_dump()


def collapse_whitespace(value: str | None) -> str:
    """Collapse repeated whitespace and trim."""

    return re.sub(r"\s+", " ", value or "").strip()


def clean_title(title: str) -> str:
    """Normalize a job title without stripping meaningful seniority words."""

    cleaned = collapse_whitespace(title)
    cleaned = re.sub(r"\s*[\-|–|—]\s*(remote|hybrid|onsite)\s*$", "", cleaned, flags=re.I)
    return cleaned.strip()


def clean_company(company_name: str) -> str:
    """Normalize company display names."""

    return collapse_whitespace(company_name)


def normalize_location_text(location_text: str | None) -> str | None:
    """Normalize location display text."""

    cleaned = collapse_whitespace(location_text)
    if not cleaned:
        return None
    return cleaned


def classify_location_type(location_text: str | None) -> str:
    """Classify location into remote, hybrid, onsite, or unknown."""

    text = collapse_whitespace(location_text).lower()
    if not text:
        return "unknown"
    if "hybrid" in text:
        return "hybrid"
    if any(token in text for token in ["remote", "work from home", "distributed"]):
        return "remote"
    if any(token in text for token in ["office", "onsite", "on-site", "in person"]):
        return "onsite"
    if re.search(r"\b[a-z .'-]+,\s*[a-z]{2,}\b", text):
        return "onsite"
    return "unknown"


def classify_employment_type(value: str | None) -> str:
    """Classify employment type from source text."""

    text = collapse_whitespace(value).lower().replace("-", " ")
    if not text:
        return "unknown"
    if "intern" in text:
        return "intern"
    if "part time" in text or "parttime" in text:
        return "part_time"
    if any(token in text for token in ["contract", "contractor", "freelance"]):
        return "contract"
    if "full time" in text or "fulltime" in text or text == "permanent":
        return "full_time"
    return "unknown"


def parse_salary(value: str | None) -> tuple[Decimal | None, Decimal | None, str | None]:
    """Parse obvious salary ranges and currencies."""

    text = collapse_whitespace(value)
    if not text:
        return None, None, None

    currency = None
    upper = text.upper()
    if "$" in text or "USD" in upper:
        currency = "USD"
    elif "EUR" in upper or "€" in text:
        currency = "EUR"
    elif "GBP" in upper or "£" in text:
        currency = "GBP"
    elif "JPY" in upper or "¥" in text:
        currency = "JPY"

    numbers: list[Decimal] = []
    for match in re.finditer(r"(?<!\w)(\d{2,3}(?:,\d{3})+|\d+(?:\.\d+)?)(\s*[kK])?", text):
        raw_number, k_suffix = match.groups()
        amount = Decimal(raw_number.replace(",", ""))
        if k_suffix:
            amount *= Decimal("1000")
        numbers.append(amount)

    if not numbers:
        return None, None, currency
    if len(numbers) == 1:
        return numbers[0], None, currency
    return min(numbers[:2]), max(numbers[:2]), currency


def extract_tags(raw: RawJobPosting) -> list[str]:
    """Extract deterministic lightweight tags from explicit tags and text."""

    tags = {collapse_whitespace(tag).lower() for tag in raw.tags if collapse_whitespace(tag)}
    haystack = " ".join(
        [
            raw.title,
            raw.description_text or "",
            raw.team_name or "",
        ]
    ).lower()
    keyword_tags = {
        "python": ["python", "django", "fastapi"],
        "backend": ["backend", "api", "service"],
        "data": ["data", "analytics", "etl"],
        "frontend": ["frontend", "react", "typescript"],
        "platform": ["platform", "infrastructure", "devops"],
    }
    for tag, keywords in keyword_tags.items():
        if any(keyword in haystack for keyword in keywords):
            tags.add(tag)
    return sorted(tags)


def stable_hash(payload: Any) -> str:
    """Return a deterministic SHA-256 hash for JSON-compatible payloads."""

    encoded = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def source_url_family(source_url: str) -> str:
    """Return conservative URL family for cross-source fingerprinting."""

    parsed = urlparse(source_url)
    return parsed.netloc.lower()


def canonical_fingerprint(
    *,
    title: str,
    company_name: str,
    location_text: str | None,
    source_url: str,
) -> str:
    """Generate a conservative cross-source fingerprint."""

    normalized_parts = [
        collapse_whitespace(title).lower(),
        collapse_whitespace(company_name).lower(),
        collapse_whitespace(location_text).lower(),
        source_url_family(source_url),
    ]
    return stable_hash("|".join(normalized_parts))


def normalize_job(raw: RawJobPosting) -> CanonicalJobData:
    """Convert one raw adapter job into canonical persistence data."""

    title = clean_title(raw.title)
    company_name = clean_company(raw.company_name)
    location_text = normalize_location_text(raw.location_text)
    location_type = classify_location_type(raw.location_text)
    employment_type = classify_employment_type(raw.employment_type_text)
    salary_min, salary_max, salary_currency = parse_salary(raw.salary_text)
    tags = extract_tags(raw)
    now = datetime.now(UTC)

    raw_payload = raw.model_dump(mode="json")
    return CanonicalJobData(
        canonical_fingerprint=canonical_fingerprint(
            title=title,
            company_name=company_name,
            location_text=location_text,
            source_url=raw.source_url,
        ),
        source_name=raw.source_name,
        source_job_id=raw.source_job_id,
        source_url=raw.source_url,
        title=title,
        company_name=company_name,
        team_name=collapse_whitespace(raw.team_name) or None,
        location_text=location_text,
        location_type=location_type,
        employment_type=employment_type,
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=salary_currency,
        description_text=collapse_whitespace(raw.description_text) or None,
        tags_json=json.dumps(tags, sort_keys=True),
        posted_at=raw.posted_at,
        scraped_at=now,
        last_seen_at=now,
        is_active=True,
        raw_hash=stable_hash(raw_payload),
    )
