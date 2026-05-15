"""Tests for POST /chat with document_context=true (RAG mode)."""

from __future__ import annotations


# ---------------------------------------------------------------------------
# document_context=false (default) — backward compatibility
# ---------------------------------------------------------------------------

def test_no_rag_sources_empty_by_default(client):
    data = client.post("/chat", json={"user_message": "Hello"}).json()
    assert data["sources"] == []


def test_no_rag_search_not_called(client, mock_llm):
    """When document_context is not set, the vector store must not be queried."""
    with __import__("unittest.mock", fromlist=["patch"]).patch(
        "app.routers.chat.search"
    ) as mock_search:
        client.post("/chat", json={"user_message": "Hello"})
        mock_search.assert_not_called()


# ---------------------------------------------------------------------------
# document_context=true — happy path
# ---------------------------------------------------------------------------

def test_rag_returns_200(client_with_rag):
    response = client_with_rag.post(
        "/chat", json={"user_message": "What is the return policy?", "document_context": True}
    )
    assert response.status_code == 200


def test_rag_response_has_sources(client_with_rag):
    data = client_with_rag.post(
        "/chat", json={"user_message": "What is the return policy?", "document_context": True}
    ).json()
    assert isinstance(data["sources"], list)
    assert len(data["sources"]) > 0


def test_rag_sources_contain_filename(client_with_rag):
    data = client_with_rag.post(
        "/chat", json={"user_message": "Return policy?", "document_context": True}
    ).json()
    # Each source should contain the filename from the mock chunks
    assert any("policy.txt" in s for s in data["sources"])


def test_rag_sources_contain_chunk_index(client_with_rag):
    data = client_with_rag.post(
        "/chat", json={"user_message": "Return policy?", "document_context": True}
    ).json()
    assert any("chunk" in s for s in data["sources"])


def test_rag_search_called_with_user_message(client_with_rag, mock_search):
    user_msg = "What is the return policy?"
    client_with_rag.post(
        "/chat", json={"user_message": user_msg, "document_context": True}
    )
    mock_search.assert_called_once()
    call_args = mock_search.call_args[0]
    assert call_args[0] == user_msg


def test_rag_llm_called_once(client_with_rag, mock_llm):
    client_with_rag.post(
        "/chat", json={"user_message": "Hello", "document_context": True}
    )
    assert mock_llm.call_count == 1


def test_rag_llm_receives_context(client_with_rag, mock_llm):
    """LLM must receive a non-empty context list when document_context=true."""
    client_with_rag.post(
        "/chat", json={"user_message": "Return policy?", "document_context": True}
    )
    call_kwargs = mock_llm.call_args[1]
    context = call_kwargs.get("context")
    assert context is not None
    assert len(context) > 0
    assert "Returns are accepted within 30 days." in context


def test_rag_still_returns_assistant_response(client_with_rag):
    data = client_with_rag.post(
        "/chat", json={"user_message": "Return policy?", "document_context": True}
    ).json()
    assert data["assistant_response"] == "Mocked assistant reply."


def test_rag_persists_conversation_history(client_with_rag):
    """RAG mode must still persist messages to SQLite like normal mode."""
    first = client_with_rag.post(
        "/chat", json={"user_message": "First", "document_context": True}
    ).json()
    conv_id = first["conversation_id"]

    second = client_with_rag.post(
        "/chat",
        json={"conversation_id": conv_id, "user_message": "Second", "document_context": True},
    ).json()
    assert second["conversation_id"] == conv_id


def test_rag_conversation_history_grows(client_with_rag):
    first = client_with_rag.post(
        "/chat", json={"user_message": "First", "document_context": True}
    ).json()
    conv_id = first["conversation_id"]

    client_with_rag.post(
        "/chat",
        json={"conversation_id": conv_id, "user_message": "Second", "document_context": True},
    )

    history = client_with_rag.get(f"/chat/conversations/{conv_id}").json()
    assert len(history["messages"]) == 4  # user+assistant × 2 turns


# ---------------------------------------------------------------------------
# Vector store error in RAG mode
# ---------------------------------------------------------------------------

def test_rag_search_error_returns_503(client_search_error):
    response = client_search_error.post(
        "/chat", json={"user_message": "Return policy?", "document_context": True}
    )
    assert response.status_code == 503


def test_rag_search_error_has_detail(client_search_error):
    data = client_search_error.post(
        "/chat", json={"user_message": "Return policy?", "document_context": True}
    ).json()
    assert "detail" in data
    assert len(data["detail"]) > 0


def test_rag_search_error_does_not_expose_key(client_search_error):
    data = client_search_error.post(
        "/chat", json={"user_message": "Return policy?", "document_context": True}
    ).json()
    assert "sk-" not in data.get("detail", "")
