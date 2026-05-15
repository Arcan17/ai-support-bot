"""Shared fixtures: in-memory SQLite DB and mocked LLM."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# ---------------------------------------------------------------------------
# In-memory test database
# StaticPool ensures all sessions share the SAME in-memory connection,
# so tables created in setup_test_db are visible in override_get_db.
# ---------------------------------------------------------------------------

test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    """Yield a session bound to the in-memory test database."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_test_db():
    """Create tables before each test and drop them after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def mock_llm():
    """Patch get_ai_response so tests never call the real OpenAI API."""
    with patch(
        "app.routers.chat.get_ai_response",
        new_callable=AsyncMock,
        return_value="Mocked assistant reply.",
    ) as mock:
        yield mock


@pytest.fixture()
def client(mock_llm):
    """TestClient with the in-memory DB and mocked LLM injected."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
