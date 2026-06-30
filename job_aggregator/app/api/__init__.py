"""API package for FastAPI application components."""
"""API package exports."""

from job_aggregator.app.api.app import create_app

__all__ = ["create_app"]
