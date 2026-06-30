"""Repository for adapter checkpoints."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from job_aggregator.app.db.models import SourceCheckpoint


class CheckpointsRepository:
    """Persistence operations for source checkpoints."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, adapter_name: str, scope_key: str) -> SourceCheckpoint | None:
        """Return a checkpoint by adapter and scope."""

        statement = select(SourceCheckpoint).where(
            SourceCheckpoint.adapter_name == adapter_name,
            SourceCheckpoint.scope_key == scope_key,
        )
        return self.session.scalar(statement)

    def upsert(
        self,
        *,
        adapter_name: str,
        scope_key: str,
        cursor_value: str,
    ) -> SourceCheckpoint:
        """Create or update a checkpoint."""

        checkpoint = self.get(adapter_name, scope_key)
        if checkpoint is None:
            checkpoint = SourceCheckpoint(
                adapter_name=adapter_name,
                scope_key=scope_key,
                cursor_value=cursor_value,
            )
            self.session.add(checkpoint)
        else:
            checkpoint.cursor_value = cursor_value

        self.session.flush()
        return checkpoint
