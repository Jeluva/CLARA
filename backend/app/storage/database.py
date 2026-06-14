"""Database engine, session factory and declarative base.

SQLite in dev, Postgres in prod — only the URL changes (see config). The
`Base` here is the single registry every model imports, so Alembic's autogenerate
and `Base.metadata.create_all` see the full schema.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# check_same_thread is a SQLite-only knob; harmless to compute conditionally.
_connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base shared by all models."""


def get_db() -> Iterator[Session]:
    """FastAPI dependency: yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
