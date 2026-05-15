"""LLM service: builds conversation history and calls OpenAI via LangChain."""

from __future__ import annotations

from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.config import settings


SYSTEM_PROMPT = (
    "You are a helpful customer support assistant. "
    "Be concise, friendly, and professional. "
    "Answer questions clearly and offer to help further if needed."
)


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
    """Call the LLM and return the assistant reply as a plain string."""
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.7,
    )
    messages = _build_messages(history, user_message)
    response = await llm.ainvoke(messages)
    return str(response.content)
