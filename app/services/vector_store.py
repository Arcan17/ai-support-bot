"""Vector store: embed document chunks and retrieve relevant context via ChromaDB."""

from __future__ import annotations

import logging

import chromadb
from langchain_openai import OpenAIEmbeddings

from app.config import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "documents"
EMBEDDING_MODEL = "text-embedding-3-small"


class VectorStoreError(Exception):
    """Raised when an embedding or vector store operation fails.

    The router catches this and returns HTTP 503.
    The original cause is chained but never forwarded to the client.
    """


# ---------------------------------------------------------------------------
# Internal helpers (replaceable in tests via module-level patching)
# ---------------------------------------------------------------------------

def _get_client() -> chromadb.ClientAPI:
    return chromadb.PersistentClient(path=settings.chroma_path)


def _get_collection(client: chromadb.ClientAPI) -> chromadb.Collection:
    return client.get_or_create_collection(COLLECTION_NAME)


def _get_embeddings_model() -> OpenAIEmbeddings:
    if not settings.openai_api_key:
        raise VectorStoreError(
            "OpenAI API key is not configured. "
            "Set the OPENAI_API_KEY environment variable."
        )
    return OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        api_key=settings.openai_api_key,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def add_chunks(
    chunks: list[str],
    document_id: int,
    filename: str,
) -> None:
    """Embed *chunks* and store them in ChromaDB with document metadata.

    Raises:
        VectorStoreError: if the API key is missing or the operation fails.
    """
    if not chunks:
        return

    try:
        model = _get_embeddings_model()
        embeddings = await model.aembed_documents(chunks)

        client = _get_client()
        collection = _get_collection(client)

        ids = [f"doc_{document_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {"document_id": document_id, "filename": filename, "chunk_index": i}
            for i in range(len(chunks))
        ]

        collection.add(
            documents=chunks,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas,
        )
        logger.info(
            "Stored %d chunks — document_id=%d filename=%s",
            len(chunks),
            document_id,
            filename,
        )

    except VectorStoreError:
        raise
    except Exception as exc:
        logger.error("add_chunks failed: %s — %s", type(exc).__name__, exc)
        raise VectorStoreError(
            "Failed to store document embeddings. Please try again."
        ) from exc


async def search(
    query: str,
    n_results: int = 3,
) -> list[dict[str, str]]:
    """Return the *n_results* most relevant chunks for *query*.

    Returns an empty list when no documents have been uploaded yet.

    Raises:
        VectorStoreError: if the API key is missing or the operation fails.
    """
    try:
        model = _get_embeddings_model()
        query_embedding = await model.aembed_query(query)

        client = _get_client()
        collection = _get_collection(client)

        count = collection.count()
        if count == 0:
            return []

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, count),
        )

        chunks: list[dict[str, str]] = []
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i]
            chunks.append(
                {
                    "content": doc,
                    "filename": str(meta["filename"]),
                    "chunk_index": str(meta["chunk_index"]),
                }
            )
        return chunks

    except VectorStoreError:
        raise
    except Exception as exc:
        logger.error("search failed: %s — %s", type(exc).__name__, exc)
        raise VectorStoreError(
            "Failed to search the document store. Please try again."
        ) from exc
