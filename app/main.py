"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.config import settings
from app.database import create_tables
from app.routers.chat import router as chat_router
from app.routers.documents import router as documents_router
from app.schemas import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Run startup/shutdown logic."""
    create_tables()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Customer support chatbot API powered by FastAPI + LangChain + OpenAI. "
        "Supports multi-turn conversations and RAG over uploaded documents (.txt, .pdf, .csv)."
    ),
    lifespan=lifespan,
)

app.include_router(chat_router)
app.include_router(documents_router)


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    """Liveness probe."""
    return HealthResponse(status="ok", version=settings.app_version)
