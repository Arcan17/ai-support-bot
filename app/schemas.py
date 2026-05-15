"""Pydantic v2 schemas for request/response validation."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Payload for POST /chat."""

    conversation_id: Optional[str] = None
    user_message: str


class ChatResponse(BaseModel):
    """Response returned by POST /chat."""

    conversation_id: str
    user_message: str
    assistant_response: str


class MessageOut(BaseModel):
    """A single message serialized for API output."""

    id: int
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationHistory(BaseModel):
    """Full history for a conversation."""

    conversation_id: str
    messages: list[MessageOut]


class HealthResponse(BaseModel):
    """Response from GET /health."""

    status: str
    version: str
