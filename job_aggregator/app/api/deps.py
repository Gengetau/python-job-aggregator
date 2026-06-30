"""FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session


def get_db(request: Request) -> Iterator[Session]:
    """Yield a DB session from the app session factory."""

    session_factory = request.app.state.session_factory
    with session_factory() as session:
        yield session
