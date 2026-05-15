"""Pydantic v2 schemas for request/response validation."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Payload for POST /chat."""

    conversation_id: Optional[str] = Field(
        default=None,
        max_length=100,
        examples=["3f2a1b4c-8e1a-4b2c-9d3e-5f6a7b8c9d0e"],
        description="Omit to start a new conversation; include to continue an existing one.",
    )
    user_message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        examples=["What is your return policy?"],
        description="The user's message. Must be between 1 and 4000 characters.",
    )
    document_context: bool = Field(
        default=False,
        description=(
            "If true, the bot searches uploaded documents for relevant context "
            "before calling the LLM. Returned sources are included in the response."
        ),
    )


class ChatResponse(BaseModel):
    """Response returned by POST /chat."""

    conversation_id: str
    user_message: str
    assistant_response: str
    sources: list[str] = Field(
        default=[],
        description="Document chunks used to generate the response (populated when document_context=true).",
    )


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


class DocumentUploadResponse(BaseModel):
    """Response from POST /documents/upload."""

    document_id: int
    filename: str
    chunk_count: int
    message: str


class HealthResponse(BaseModel):
    """Response from GET /health."""

    status: str
    version: str
