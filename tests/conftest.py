"""Shared fixtures: in-memory SQLite DB and mocked LLM / vector store."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.services.llm_service import LLMError
from app.services.vector_store import VectorStoreError

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


# ---------------------------------------------------------------------------
# LLM mocks
# ---------------------------------------------------------------------------

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
    """TestClient with in-memory DB and mocked LLM (happy path)."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def client_llm_error():
    """TestClient where get_ai_response always raises LLMError."""
    with patch(
        "app.routers.chat.get_ai_response",
        new_callable=AsyncMock,
        side_effect=LLMError("The AI service is temporarily unavailable. Please try again."),
    ):
        app.dependency_overrides[get_db] = override_get_db
        with TestClient(app) as c:
            yield c
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Vector store mocks
# ---------------------------------------------------------------------------

MOCK_CHUNKS = [
    {"content": "Returns are accepted within 30 days.", "filename": "policy.txt", "chunk_index": "0"},
    {"content": "Refunds take 5–7 business days.", "filename": "policy.txt", "chunk_index": "1"},
]


@pytest.fixture()
def mock_search():
    """Patch search() to return two canned document chunks."""
    with patch(
        "app.routers.chat.search",
        new_callable=AsyncMock,
        return_value=MOCK_CHUNKS,
    ) as mock:
        yield mock


@pytest.fixture()
def mock_add_chunks():
    """Patch add_chunks() so document upload tests never call ChromaDB/OpenAI."""
    with patch(
        "app.routers.documents.add_chunks",
        new_callable=AsyncMock,
    ) as mock:
        yield mock


@pytest.fixture()
def client_with_rag(mock_llm, mock_search):
    """TestClient with LLM + vector store both mocked (RAG happy path)."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def client_upload(mock_add_chunks):
    """TestClient for document upload tests (add_chunks mocked)."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def client_search_error(mock_llm):
    """TestClient where search() always raises VectorStoreError."""
    with patch(
        "app.routers.chat.search",
        new_callable=AsyncMock,
        side_effect=VectorStoreError("Failed to search the document store. Please try again."),
    ):
        app.dependency_overrides[get_db] = override_get_db
        with TestClient(app) as c:
            yield c
        app.dependency_overrides.clear()


@pytest.fixture()
def client_add_chunks_error():
    """TestClient where add_chunks() always raises VectorStoreError."""
    with patch(
        "app.routers.documents.add_chunks",
        new_callable=AsyncMock,
        side_effect=VectorStoreError("Failed to store document embeddings. Please try again."),
    ):
        app.dependency_overrides[get_db] = override_get_db
        with TestClient(app) as c:
            yield c
        app.dependency_overrides.clear()
