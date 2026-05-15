"""Documents router: POST /documents/upload."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Document
from app.schemas import DocumentUploadResponse
from app.services.document_service import extract_text, split_text, validate_extension
from app.services.vector_store import VectorStoreError, add_chunks

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    """Upload a document (.txt, .pdf, or .csv), extract text, split into chunks,
    create OpenAI embeddings, and store in ChromaDB for RAG retrieval.

    - Returns **422** for unsupported file types, empty files, or no extractable text.
    - Returns **413** if the file exceeds 10 MB.
    - Returns **503** if the embedding service is unavailable.
    """
    filename = file.filename or "unknown"

    # 1 — Validate extension
    try:
        validate_extension(filename)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # 2 — Read content
    content = await file.read()

    if len(content) == 0:
        raise HTTPException(status_code=422, detail="File is empty.")

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds the 10 MB size limit.")

    # 3 — Extract text
    try:
        text = extract_text(content, filename)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not extract text: {exc}")

    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail="No text could be extracted from the document.",
        )

    # 4 — Split into chunks
    chunks = split_text(text)
    if not chunks:
        raise HTTPException(
            status_code=422,
            detail="Document produced no usable text chunks.",
        )

    # 5 — Persist metadata in SQLite
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown"
    doc = Document(filename=filename, content_type=ext, chunk_count=len(chunks))
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # 6 — Embed and store in ChromaDB
    try:
        await add_chunks(chunks, doc.id, doc.filename)
    except VectorStoreError as exc:
        # Roll back the SQLite record — embedding failed, nothing is usable
        db.delete(doc)
        db.commit()
        raise HTTPException(status_code=503, detail=str(exc))

    logger.info(
        "Document uploaded — id=%d filename=%s chunks=%d",
        doc.id,
        doc.filename,
        len(chunks),
    )

    return DocumentUploadResponse(
        document_id=doc.id,
        filename=doc.filename,
        chunk_count=len(chunks),
        message=f"Document uploaded and indexed successfully. {len(chunks)} chunks stored.",
    )
