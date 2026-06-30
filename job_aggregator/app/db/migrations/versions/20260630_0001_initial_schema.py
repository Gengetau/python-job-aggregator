"""Create initial job aggregation schema.

Revision ID: 20260630_0001
Revises:
Create Date: 2026-06-30 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260630_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crawl_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("trigger_type", sa.String(length=24), nullable=False),
        sa.Column("adapter_scope", sa.Text(), nullable=False),
        sa.Column("jobs_seen", sa.Integer(), nullable=False),
        sa.Column("jobs_created", sa.Integer(), nullable=False),
        sa.Column("jobs_updated", sa.Integer(), nullable=False),
        sa.Column("jobs_deactivated", sa.Integer(), nullable=False),
        sa.Column("errors_count", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "status IN ('running', 'success', 'partial_success', 'failed')",
            name="ck_crawl_runs_status",
        ),
        sa.CheckConstraint(
            "trigger_type IN ('manual', 'scheduled', 'api')",
            name="ck_crawl_runs_trigger_type",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crawl_runs_started_at", "crawl_runs", ["started_at"])
    op.create_index("ix_crawl_runs_status", "crawl_runs", ["status"])

    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("canonical_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("source_name", sa.String(length=80), nullable=False),
        sa.Column("source_job_id", sa.String(length=160), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("company_name", sa.String(length=240), nullable=False),
        sa.Column("team_name", sa.String(length=240), nullable=True),
        sa.Column("location_text", sa.String(length=300), nullable=True),
        sa.Column("location_type", sa.String(length=24), nullable=False),
        sa.Column("employment_type", sa.String(length=24), nullable=False),
        sa.Column("salary_min", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("salary_max", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("salary_currency", sa.String(length=3), nullable=True),
        sa.Column("description_text", sa.Text(), nullable=True),
        sa.Column("tags_json", sa.Text(), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("raw_hash", sa.String(length=128), nullable=False),
        sa.CheckConstraint(
            "employment_type IN ('full_time', 'part_time', 'contract', 'intern', 'unknown')",
            name="ck_jobs_employment_type",
        ),
        sa.CheckConstraint(
            "location_type IN ('onsite', 'hybrid', 'remote', 'unknown')",
            name="ck_jobs_location_type",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_name", "source_job_id", name="uq_jobs_source_identity"),
    )
    op.create_index("ix_jobs_canonical_fingerprint", "jobs", ["canonical_fingerprint"])
    op.create_index("ix_jobs_company_name", "jobs", ["company_name"])
    op.create_index("ix_jobs_employment_type", "jobs", ["employment_type"])
    op.create_index("ix_jobs_is_active", "jobs", ["is_active"])
    op.create_index("ix_jobs_location_type", "jobs", ["location_type"])
    op.create_index("ix_jobs_source_name", "jobs", ["source_name"])

    op.create_table(
        "source_checkpoints",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("adapter_name", sa.String(length=80), nullable=False),
        sa.Column("scope_key", sa.String(length=240), nullable=False),
        sa.Column("cursor_value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "adapter_name",
            "scope_key",
            name="uq_source_checkpoints_adapter_scope",
        ),
    )
    op.create_index("ix_source_checkpoints_adapter_name", "source_checkpoints", ["adapter_name"])

    op.create_table(
        "crawl_run_errors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("adapter_name", sa.String(length=80), nullable=False),
        sa.Column("stage", sa.String(length=80), nullable=False),
        sa.Column("target_url", sa.Text(), nullable=True),
        sa.Column("error_type", sa.String(length=160), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["crawl_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crawl_run_errors_adapter_name", "crawl_run_errors", ["adapter_name"])
    op.create_index("ix_crawl_run_errors_run_id", "crawl_run_errors", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_crawl_run_errors_run_id", table_name="crawl_run_errors")
    op.drop_index("ix_crawl_run_errors_adapter_name", table_name="crawl_run_errors")
    op.drop_table("crawl_run_errors")

    op.drop_index("ix_source_checkpoints_adapter_name", table_name="source_checkpoints")
    op.drop_table("source_checkpoints")

    op.drop_index("ix_jobs_source_name", table_name="jobs")
    op.drop_index("ix_jobs_location_type", table_name="jobs")
    op.drop_index("ix_jobs_is_active", table_name="jobs")
    op.drop_index("ix_jobs_employment_type", table_name="jobs")
    op.drop_index("ix_jobs_company_name", table_name="jobs")
    op.drop_index("ix_jobs_canonical_fingerprint", table_name="jobs")
    op.drop_table("jobs")

    op.drop_index("ix_crawl_runs_status", table_name="crawl_runs")
    op.drop_index("ix_crawl_runs_started_at", table_name="crawl_runs")
    op.drop_table("crawl_runs")
