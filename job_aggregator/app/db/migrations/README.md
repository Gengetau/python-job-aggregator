# Database Migrations

Loop 2 uses SQLAlchemy metadata initialization through:

```bash
job-aggregator db init
```

Alembic is included in the project dependencies, and the ORM model boundaries are
kept migration-friendly. Once the early schema stabilizes, this directory should
hold Alembic revision scripts instead of relying only on `Base.metadata.create_all`.
