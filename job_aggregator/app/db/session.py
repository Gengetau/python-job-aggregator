"""Database engine, session, and initialization helpers."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from job_aggregator.app.core.config import get_settings
from job_aggregator.app.db.models import Base


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _ensure_sqlite_parent(database_url: str) -> None:
    """Create the parent directory for file-backed SQLite URLs."""

    url = make_url(database_url)
    if not url.drivername.startswith("sqlite"):
        return
    if not url.database or url.database == ":memory:":
        return
    if url.query.get("mode") == "memory" or url.database.startswith("file:"):
        return

    database_path = Path(url.database)
    if not database_path.is_absolute():
        database_path = Path.cwd() / database_path
    database_path.parent.mkdir(parents=True, exist_ok=True)


def make_engine(database_url: str | None = None, *, echo: bool = False) -> Engine:
    """Create an SQLAlchemy engine for the configured database."""

    resolved_url = database_url or get_settings().database_url
    _ensure_sqlite_parent(resolved_url)
    url = make_url(resolved_url)
    connect_args = {"check_same_thread": False} if url.drivername.startswith("sqlite") else {}
    engine_kwargs = {"connect_args": connect_args}
    if url.drivername.startswith("sqlite") and url.database == ":memory:":
        engine_kwargs["poolclass"] = StaticPool
    return create_engine(resolved_url, echo=echo, **engine_kwargs)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a session factory bound to an engine."""

    return sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        class_=Session,
    )


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """Provide a transactional session scope."""

    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_database(database_url: str | None = None, *, echo: bool = False) -> Engine:
    """Initialize database tables and return the created engine."""

    engine = make_engine(database_url, echo=echo)
    Base.metadata.create_all(bind=engine)
    return engine


def upgrade_database(database_url: str | None = None) -> None:
    """Apply Alembic migrations through the latest revision."""

    from alembic import command
    from alembic.config import Config

    resolved_url = database_url or get_settings().database_url
    _ensure_sqlite_parent(resolved_url)
    config = Config(str(_project_root() / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", resolved_url)
    command.upgrade(config, "head")


def get_session(database_url: str | None = None) -> Iterator[Session]:
    """Yield a session for dependency injection style usage."""

    engine = make_engine(database_url)
    session_factory = create_session_factory(engine)
    with session_scope(session_factory) as session:
        yield session
