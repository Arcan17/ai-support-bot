"""Tests for GET /chat/conversations/{conversation_id}."""

from __future__ import annotations


def test_get_conversation_not_found(client):
    response = client.get("/chat/conversations/nonexistent-id")
    assert response.status_code == 404


def test_get_conversation_after_chat(client):
    first = client.post("/chat", json={"user_message": "Hello"}).json()
    conv_id = first["conversation_id"]

    response = client.get(f"/chat/conversations/{conv_id}")
    assert response.status_code == 200


def test_get_conversation_has_two_messages(client):
    first = client.post("/chat", json={"user_message": "Hello"}).json()
    conv_id = first["conversation_id"]

    data = client.get(f"/chat/conversations/{conv_id}").json()
    assert len(data["messages"]) == 2


def test_get_conversation_message_roles(client):
    first = client.post("/chat", json={"user_message": "Hello"}).json()
    conv_id = first["conversation_id"]

    messages = client.get(f"/chat/conversations/{conv_id}").json()["messages"]
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


def test_get_conversation_message_content(client):
    first = client.post("/chat", json={"user_message": "Hello world"}).json()
    conv_id = first["conversation_id"]

    messages = client.get(f"/chat/conversations/{conv_id}").json()["messages"]
    assert messages[0]["content"] == "Hello world"
    assert messages[1]["content"] == "Mocked assistant reply."


def test_get_conversation_grows_with_turns(client):
    first = client.post("/chat", json={"user_message": "Turn 1"}).json()
    conv_id = first["conversation_id"]

    client.post("/chat", json={"conversation_id": conv_id, "user_message": "Turn 2"})

    messages = client.get(f"/chat/conversations/{conv_id}").json()["messages"]
    assert len(messages) == 4  # user+assistant × 2 turns


def test_get_conversation_returns_correct_id(client):
    first = client.post("/chat", json={"user_message": "Hi"}).json()
    conv_id = first["conversation_id"]

    data = client.get(f"/chat/conversations/{conv_id}").json()
    assert data["conversation_id"] == conv_id
