"""Helpers for building adapter runtime contexts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from job_aggregator.app.adapters.base import AdapterContext

SCOPE_OPTION_KEYS = ("scope_key", "board_token", "company_slug", "listing_url")


def context_from_options(options: Mapping[str, Any]) -> AdapterContext:
    """Build an adapter context from operator-supplied options."""

    option_values = dict(options)
    scope_key = option_values.pop("scope_key", None)
    if scope_key is None:
        for key in SCOPE_OPTION_KEYS[1:]:
            value = option_values.get(key)
            if value:
                scope_key = value
                break
    return AdapterContext(
        scope_key=str(scope_key) if scope_key is not None else None,
        options=option_values,
    )


def contexts_from_options(
    options_by_adapter: Mapping[str, Mapping[str, Any]] | None,
) -> dict[str, AdapterContext]:
    """Build collector contexts from adapter-name keyed option mappings."""

    if not options_by_adapter:
        return {}
    return {
        adapter_name: context_from_options(options)
        for adapter_name, options in options_by_adapter.items()
    }
