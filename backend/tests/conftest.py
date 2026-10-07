"""Shared pytest fixtures.

Tests run against an isolated in-memory SQLite database so they need no
external Postgres/Redis — the production stack still targets Postgres.
"""
from __future__ import annotations

import os

# Force a throwaway SQLite DB *before* app modules read settings.
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")

import pytest
from app.db.session import get_db
from app.main import app
from app.models import Base
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def engine():
    # Fresh in-memory DB per test for isolation (StaticPool keeps one connection).
    eng = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db_session(engine):
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
