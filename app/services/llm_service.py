"""LLM service: builds conversation history and calls OpenAI via LangChain."""

from __future__ import annotations

import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a helpful customer support assistant. "
    "Be concise, friendly, and professional. "
    "Answer questions clearly and offer to help further if needed."
)


class LLMError(Exception):
    """Raised when the LLM call fails or is not configured.

    The router catches this and returns HTTP 503 with the message as detail.
    The original exception is chained but never exposed to the client.
    """


def _build_messages(
    history: list[dict[str, str]],
    user_message: str,
) -> list:
    """Convert stored history + new user message into LangChain message objects."""
    messages: list = [SystemMessage(content=SYSTEM_PROMPT)]
    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=user_message))
    return messages


async def get_ai_response(
    history: list[dict[str, str]],
    user_message: str,
) -> str:
    """Call the LLM and return the assistant reply as a plain string.

    Raises:
        LLMError: if the API key is missing or the LLM call fails for any reason.
    """
    if not settings.openai_api_key:
        raise LLMError(
            "OpenAI API key is not configured. "
            "Set the OPENAI_API_KEY environment variable."
        )

    try:
        llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.7,
        )
        messages = _build_messages(history, user_message)
        response = await llm.ainvoke(messages)
        return str(response.content)
    except LLMError:
        raise
    except Exception as exc:
        logger.error("LLM call failed: %s — %s", type(exc).__name__, exc)
        raise LLMError("The AI service is temporarily unavailable. Please try again.") from exc
