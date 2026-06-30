"""Checkpoint helpers used by the collector."""

from __future__ import annotations

from job_aggregator.app.adapters.base import AdapterContext, BaseJobAdapter
from job_aggregator.app.db.repositories.checkpoints import CheckpointsRepository


def checkpoint_scope(adapter: BaseJobAdapter, context: AdapterContext | None) -> str:
    """Return the stable checkpoint scope for an adapter execution."""

    return (context.scope_key if context else None) or adapter.source_scope


def context_with_checkpoint(
    adapter: BaseJobAdapter,
    repository: CheckpointsRepository,
    context: AdapterContext | None = None,
) -> AdapterContext:
    """Return context populated with any persisted checkpoint."""

    scope_key = checkpoint_scope(adapter, context)
    checkpoint = repository.get(adapter.name, scope_key)
    options = dict(context.options) if context else {}
    return AdapterContext(
        scope_key=scope_key,
        checkpoint=checkpoint.cursor_value if checkpoint else None,
        options=options,
    )
