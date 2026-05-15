"""Chat router: POST /chat and GET /chat/conversations/{conversation_id}."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Message
from app.schemas import ChatRequest, ChatResponse, ConversationHistory, MessageOut
from app.services.llm_service import LLMError, get_ai_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    """Send a message and receive the assistant reply.

    If *conversation_id* is omitted a new conversation is started automatically.
    History for the given conversation is loaded from SQLite, passed to the LLM,
    and both the user message and assistant reply are persisted.

    Returns HTTP 503 if the LLM service is unavailable or not configured.
    """
    conversation_id = payload.conversation_id or str(uuid.uuid4())

    # Load existing history for this conversation
    history_rows = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .all()
    )
    history = [{"role": m.role, "content": m.content} for m in history_rows]

    # Call the LLM — catch config/network errors and return 503
    try:
        assistant_reply = await get_ai_response(history, payload.user_message)
    except LLMError as exc:
        logger.warning("LLM unavailable for conversation %s: %s", conversation_id, exc)
        raise HTTPException(status_code=503, detail=str(exc))

    # Persist user message + assistant reply
    db.add(Message(conversation_id=conversation_id, role="user", content=payload.user_message))
    db.add(Message(conversation_id=conversation_id, role="assistant", content=assistant_reply))
    db.commit()

    logger.info("Chat OK — conversation=%s messages_in_history=%d", conversation_id, len(history))

    return ChatResponse(
        conversation_id=conversation_id,
        user_message=payload.user_message,
        assistant_response=assistant_reply,
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationHistory)
def get_conversation(
    conversation_id: str, db: Session = Depends(get_db)
) -> ConversationHistory:
    """Return full message history for a conversation."""
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .all()
    )
    if not messages:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ConversationHistory(
        conversation_id=conversation_id,
        messages=[MessageOut.model_validate(m) for m in messages],
    )
