# Database Migrations

This directory contains Alembic migrations for the persisted job aggregation
schema.

Apply migrations with the operator CLI:

```bash
job-aggregator db init
```

`db init` resolves `JOB_AGGREGATOR_DATABASE_URL`, creates the parent directory for
file-backed SQLite databases, and upgrades the database to the current Alembic
head revision.

Create future revisions from the repository root:

```bash
alembic revision --autogenerate -m "describe change"
```
