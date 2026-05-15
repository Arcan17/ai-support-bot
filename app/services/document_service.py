"""Document ingestion: text extraction and chunking."""

from __future__ import annotations

import io

import pypdf
from langchain_text_splitters import RecursiveCharacterTextSplitter

ALLOWED_EXTENSIONS = {".txt", ".pdf", ".csv"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def validate_extension(filename: str) -> str:
    """Return the lowercase extension or raise ValueError if not allowed."""
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'. "
            f"Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    return ext


def extract_text(content: bytes, filename: str) -> str:
    """Extract plain text from the raw file bytes.

    Supports .txt, .csv (decoded as UTF-8) and .pdf (via pypdf).
    Raises ValueError if the file type is not supported.
    """
    ext = validate_extension(filename)

    if ext in {".txt", ".csv"}:
        return content.decode("utf-8", errors="replace").strip()

    if ext == ".pdf":
        reader = pypdf.PdfReader(io.BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages).strip()

    return ""  # unreachable but satisfies type checker


def split_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[str]:
    """Split text into overlapping chunks for embedding.

    Returns an empty list if the text is blank.
    """
    if not text.strip():
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return [chunk for chunk in splitter.split_text(text) if chunk.strip()]
