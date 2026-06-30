"""Scheduler-facing helpers for future timed crawl entrypoints."""

from __future__ import annotations


def describe_scheduler() -> str:
    """Return current scheduler support status."""

    return "scheduled crawls are represented by trigger_type='scheduled' runs in v1"
