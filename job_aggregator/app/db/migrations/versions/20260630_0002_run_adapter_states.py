"""Add crawl run adapter state table.

Revision ID: 20260630_0002
Revises: 20260630_0001
Create Date: 2026-06-30 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260630_0002"
down_revision = "20260630_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crawl_run_adapter_states",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("adapter_name", sa.String(length=80), nullable=False),
        sa.Column("scope_key", sa.String(length=240), nullable=False),
        sa.Column("checkpoint_before", sa.Text(), nullable=True),
        sa.Column("checkpoint_after", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["crawl_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "run_id",
            "adapter_name",
            "scope_key",
            name="uq_crawl_run_adapter_states_run_adapter_scope",
        ),
    )
    op.create_index(
        "ix_crawl_run_adapter_states_adapter_name",
        "crawl_run_adapter_states",
        ["adapter_name"],
    )
    op.create_index(
        "ix_crawl_run_adapter_states_run_id",
        "crawl_run_adapter_states",
        ["run_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_crawl_run_adapter_states_run_id",
        table_name="crawl_run_adapter_states",
    )
    op.drop_index(
        "ix_crawl_run_adapter_states_adapter_name",
        table_name="crawl_run_adapter_states",
    )
    op.drop_table("crawl_run_adapter_states")
