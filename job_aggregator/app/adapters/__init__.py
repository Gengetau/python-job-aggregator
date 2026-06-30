"""Source adapter package exports."""

from job_aggregator.app.adapters.base import (
    AdapterContext,
    AdapterError,
    AdapterFetchMode,
    AdapterMetadata,
    AdapterResult,
    BaseJobAdapter,
    RawJobPosting,
)
from job_aggregator.app.adapters.custom_page import CustomPageAdapter, CustomPageConfig
from job_aggregator.app.adapters.demo import DemoAdapter
from job_aggregator.app.adapters.greenhouse import GreenhouseAdapter
from job_aggregator.app.adapters.lever import LeverAdapter

__all__ = [
    "AdapterContext",
    "AdapterError",
    "AdapterFetchMode",
    "AdapterMetadata",
    "AdapterResult",
    "BaseJobAdapter",
    "CustomPageAdapter",
    "CustomPageConfig",
    "DemoAdapter",
    "GreenhouseAdapter",
    "LeverAdapter",
    "RawJobPosting",
]
