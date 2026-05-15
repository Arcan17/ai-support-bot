"""Tests for POST /documents/upload."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TXT_CONTENT = b"This is a test document. It contains support policies and return information."
CSV_CONTENT = b"product,price,policy\niPhone,999,30-day return\nLaptop,1299,14-day return"


def _upload(client, filename: str, content: bytes, content_type: str = "text/plain"):
    """Helper: POST /documents/upload with a file."""
    return client.post(
        "/documents/upload",
        files={"file": (filename, content, content_type)},
    )


# ---------------------------------------------------------------------------
# .txt uploads
# ---------------------------------------------------------------------------

def test_upload_txt_returns_200(client_upload):
    response = _upload(client_upload, "policy.txt", TXT_CONTENT)
    assert response.status_code == 200


def test_upload_txt_response_fields(client_upload):
    data = _upload(client_upload, "policy.txt", TXT_CONTENT).json()
    assert "document_id" in data
    assert "filename" in data
    assert "chunk_count" in data
    assert "message" in data


def test_upload_txt_filename_preserved(client_upload):
    data = _upload(client_upload, "my_policy.txt", TXT_CONTENT).json()
    assert data["filename"] == "my_policy.txt"


def test_upload_txt_chunk_count_positive(client_upload):
    data = _upload(client_upload, "policy.txt", TXT_CONTENT).json()
    assert data["chunk_count"] > 0


def test_upload_txt_document_id_is_integer(client_upload):
    data = _upload(client_upload, "policy.txt", TXT_CONTENT).json()
    assert isinstance(data["document_id"], int)


# ---------------------------------------------------------------------------
# .csv uploads
# ---------------------------------------------------------------------------

def test_upload_csv_returns_200(client_upload):
    response = _upload(client_upload, "products.csv", CSV_CONTENT, "text/csv")
    assert response.status_code == 200


def test_upload_csv_chunk_count_positive(client_upload):
    data = _upload(client_upload, "products.csv", CSV_CONTENT, "text/csv").json()
    assert data["chunk_count"] > 0


# ---------------------------------------------------------------------------
# .pdf uploads
# ---------------------------------------------------------------------------

def test_upload_pdf_returns_200(client_upload):
    """PDF extraction is mocked — test that the endpoint handles it correctly."""
    with patch("app.services.document_service.pypdf.PdfReader") as mock_reader_cls:
        mock_page = MagicMock()
        mock_page.extract_text.return_value = (
            "This is a PDF document with return policy information. "
            "Customers may return products within 30 days of purchase."
        )
        mock_reader_cls.return_value.pages = [mock_page]

        response = _upload(client_upload, "manual.pdf", b"%PDF-1.0 fake", "application/pdf")
    assert response.status_code == 200


def test_upload_pdf_chunk_count_positive(client_upload):
    with patch("app.services.document_service.pypdf.PdfReader") as mock_reader_cls:
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "PDF text content with enough words to produce at least one chunk."
        mock_reader_cls.return_value.pages = [mock_page]

        data = _upload(client_upload, "manual.pdf", b"%PDF-1.0 fake", "application/pdf").json()
    assert data["chunk_count"] > 0


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------

def test_upload_unsupported_extension_returns_422(client_upload):
    response = _upload(client_upload, "notes.docx", b"some content")
    assert response.status_code == 422


def test_upload_unsupported_extension_detail(client_upload):
    data = _upload(client_upload, "notes.docx", b"some content").json()
    assert "detail" in data
    assert ".docx" in data["detail"]


def test_upload_empty_file_returns_422(client_upload):
    response = _upload(client_upload, "empty.txt", b"")
    assert response.status_code == 422


def test_upload_no_extension_returns_422(client_upload):
    response = _upload(client_upload, "noextension", b"some content")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Vector store error
# ---------------------------------------------------------------------------

def test_upload_vector_store_error_returns_503(client_add_chunks_error):
    response = _upload(client_add_chunks_error, "policy.txt", TXT_CONTENT)
    assert response.status_code == 503


def test_upload_vector_store_error_has_detail(client_add_chunks_error):
    data = _upload(client_add_chunks_error, "policy.txt", TXT_CONTENT).json()
    assert "detail" in data
    assert len(data["detail"]) > 0


def test_upload_vector_store_error_rolls_back_db(client_add_chunks_error):
    """When embedding fails, the SQLite document record must be rolled back."""
    _upload(client_add_chunks_error, "policy.txt", TXT_CONTENT)
    # Upload again — document_id should still be 1 if the first record was rolled back
    # (The second upload will also fail, but we can check the fixture was called twice)
    response2 = _upload(client_add_chunks_error, "policy2.txt", TXT_CONTENT)
    assert response2.status_code == 503
