"""Tests for POST /chat."""

from __future__ import annotations


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
    _, kwargs = mock_llm.call_args
    history = mock_llm.call_args[0][0]
    assert len(history) == 2  # user + assistant from first turn
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"
