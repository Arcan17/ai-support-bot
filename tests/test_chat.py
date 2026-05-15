"""Tests for POST /chat."""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_chat_returns_200(client):
    response = client.post("/chat", json={"user_message": "Hello"})
    assert response.status_code == 200


def test_chat_response_fields(client):
    data = client.post("/chat", json={"user_message": "Hello"}).json()
    assert "conversation_id" in data
    assert "user_message" in data
    assert "assistant_response" in data


def test_chat_echoes_user_message(client):
    data = client.post("/chat", json={"user_message": "Test message"}).json()
    assert data["user_message"] == "Test message"


def test_chat_returns_mocked_reply(client):
    data = client.post("/chat", json={"user_message": "Hello"}).json()
    assert data["assistant_response"] == "Mocked assistant reply."


def test_chat_auto_creates_conversation_id(client):
    data = client.post("/chat", json={"user_message": "Hi"}).json()
    conv_id = data["conversation_id"]
    assert isinstance(conv_id, str)
    assert len(conv_id) == 36  # UUID format


def test_chat_continues_existing_conversation(client):
    first = client.post("/chat", json={"user_message": "First message"}).json()
    conv_id = first["conversation_id"]

    second = client.post(
        "/chat",
        json={"conversation_id": conv_id, "user_message": "Second message"},
    ).json()
    assert second["conversation_id"] == conv_id


def test_chat_with_explicit_conversation_id(client):
    conv_id = "test-conv-id-123"
    data = client.post(
        "/chat",
        json={"conversation_id": conv_id, "user_message": "Hi"},
    ).json()
    assert data["conversation_id"] == conv_id


def test_chat_llm_called_once_per_request(client, mock_llm):
    client.post("/chat", json={"user_message": "Hello"})
    assert mock_llm.call_count == 1


def test_chat_llm_receives_history_on_second_turn(client, mock_llm):
    first = client.post("/chat", json={"user_message": "First"}).json()
    conv_id = first["conversation_id"]

    client.post("/chat", json={"conversation_id": conv_id, "user_message": "Second"})

    # Second call: history should contain the first user+assistant pair
    history = mock_llm.call_args[0][0]
    assert len(history) == 2  # user + assistant from first turn
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def test_chat_empty_message_returns_422(client):
    """Empty user_message must be rejected by Pydantic (min_length=1)."""
    response = client.post("/chat", json={"user_message": ""})
    assert response.status_code == 422


def test_chat_missing_message_returns_422(client):
    """Missing user_message field must be rejected."""
    response = client.post("/chat", json={})
    assert response.status_code == 422


def test_chat_message_too_long_returns_422(client):
    """Messages over 4000 characters must be rejected (max_length=4000)."""
    response = client.post("/chat", json={"user_message": "x" * 4001})
    assert response.status_code == 422


def test_chat_message_at_max_length_returns_200(client):
    """Messages exactly 4000 characters must be accepted."""
    response = client.post("/chat", json={"user_message": "x" * 4000})
    assert response.status_code == 200


def test_chat_conversation_id_too_long_returns_422(client):
    """conversation_id over 100 characters must be rejected."""
    response = client.post(
        "/chat",
        json={"user_message": "Hi", "conversation_id": "x" * 101},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# LLM error handling
# ---------------------------------------------------------------------------

def test_chat_llm_error_returns_503(client_llm_error):
    """When the LLM fails, the API must return HTTP 503."""
    response = client_llm_error.post("/chat", json={"user_message": "Hello"})
    assert response.status_code == 503


def test_chat_llm_error_returns_json_detail(client_llm_error):
    """503 response must include a human-readable detail message."""
    data = client_llm_error.post("/chat", json={"user_message": "Hello"}).json()
    assert "detail" in data
    assert len(data["detail"]) > 0


def test_chat_llm_error_does_not_expose_key(client_llm_error):
    """Error response must never contain API key fragments."""
    data = client_llm_error.post("/chat", json={"user_message": "Hello"}).json()
    assert "sk-" not in data.get("detail", "")
