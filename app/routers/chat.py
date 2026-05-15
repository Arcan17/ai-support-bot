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
from app.services.vector_store import VectorStoreError, search

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    """Send a message and receive the assistant reply.

    If *conversation_id* is omitted a new conversation is started automatically.
    History for the given conversation is loaded from SQLite, passed to the LLM,
    and both the user message and assistant reply are persisted.

    When *document_context=true*, the most relevant uploaded document chunks
    are retrieved from ChromaDB and injected into the LLM system prompt.
    The chunks used are returned as *sources* in the response.

    Returns HTTP 503 if the LLM service or vector store is unavailable.
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

    # Optionally retrieve document context (RAG)
    context_chunks: list[dict[str, str]] = []
    if payload.document_context:
        try:
            context_chunks = await search(payload.user_message)
        except VectorStoreError as exc:
            logger.warning("Vector store unavailable: %s", exc)
            raise HTTPException(status_code=503, detail=str(exc))

    context = [c["content"] for c in context_chunks] or None
    sources = [
        f"{c['filename']} (chunk {c['chunk_index']})" for c in context_chunks
    ]

    # Call the LLM
    try:
        assistant_reply = await get_ai_response(history, payload.user_message, context=context)
    except LLMError as exc:
        logger.warning("LLM unavailable for conversation %s: %s", conversation_id, exc)
        raise HTTPException(status_code=503, detail=str(exc))

    # Persist user message + assistant reply
    db.add(Message(conversation_id=conversation_id, role="user", content=payload.user_message))
    db.add(Message(conversation_id=conversation_id, role="assistant", content=assistant_reply))
    db.commit()

    logger.info(
        "Chat OK — conversation=%s history=%d rag=%s sources=%d",
        conversation_id,
        len(history),
        payload.document_context,
        len(sources),
    )

    return ChatResponse(
        conversation_id=conversation_id,
        user_message=payload.user_message,
        assistant_response=assistant_reply,
        sources=sources,
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
