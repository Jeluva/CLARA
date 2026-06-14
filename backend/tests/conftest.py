"""Shared pytest fixtures: an isolated in-memory database per test.

Tests never touch the dev `clara.db`. Each test gets a fresh SQLite in-memory
schema built from the model metadata, so they're fast and independent.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.storage.database import Base
import app.storage.models  # noqa: F401  (registers all tables on Base.metadata)


@pytest.fixture
def db() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(
        bind=engine, autoflush=False, expire_on_commit=False
    )
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
