# AI Support Bot

**Customer support chatbot API built with FastAPI + LangChain + OpenAI. Multi-turn conversation memory + RAG over uploaded documents.**

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-0.3-1C3C3C?style=flat)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991?style=flat&logo=openai&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-vector--store-FF6B35?style=flat)
![Tests](https://img.shields.io/badge/tests-58%20passing-brightgreen?style=flat)
![CI](https://img.shields.io/github/actions/workflow/status/Arcan17/ai-support-bot/ci.yml?label=CI&logo=github)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat&logo=docker&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green?style=flat)

---

## Current Scope — v2.0.0

**v2 adds RAG (Retrieval Augmented Generation) on top of the v1 chatbot.**

What's included:
- Multi-turn conversation memory persisted in SQLite
- Document upload endpoint (.txt, .pdf, .csv)
- Text extraction, chunking, and embedding via OpenAI
- ChromaDB vector store for semantic search
- `document_context=true` flag in `/chat` injects relevant chunks into the LLM prompt
- Sources returned in the chat response (filename + chunk index)
- Input validation, graceful error handling (422 / 503), no key leaks
- 58 passing tests — all LLM and embedding calls mocked

Not in this version (planned):
- WhatsApp / Twilio integration

---

## How RAG Works

```
1. Upload a document → POST /documents/upload
   ┌─────────────┐     ┌──────────────────┐     ┌──────────────┐
   │  .txt/.pdf  │────▶│ extract + chunk  │────▶│  OpenAI      │
   │  .csv file  │     │  RecursiveText   │     │  Embeddings  │
   └─────────────┘     │  Splitter        │     └──────┬───────┘
                       └──────────────────┘            │
                                                       ▼
                                                ┌──────────────┐
                                                │  ChromaDB    │
                                                │  (local)     │
                                                └──────────────┘

2. Ask a question → POST /chat  { document_context: true }
   ┌──────────────┐     ┌──────────────┐     ┌──────────────────────────┐
   │ user_message │────▶│ embed query  │────▶│  ChromaDB similarity     │
   └──────────────┘     │ OpenAI       │     │  search → top 3 chunks   │
                        └──────────────┘     └───────────┬──────────────┘
                                                         │
                                            ┌────────────▼─────────────┐
                                            │  LLM prompt:             │
                                            │  system + DOCUMENTS +    │
                                            │  history + user_message  │
                                            └────────────┬─────────────┘
                                                         │
                                            ┌────────────▼─────────────┐
                                            │  response + sources[]    │
                                            └──────────────────────────┘
```

---

## Endpoints

### `POST /documents/upload`

Upload a document to build the knowledge base.

**Request:** multipart/form-data with field `file`

Supported types: `.txt`, `.pdf`, `.csv` — max 10 MB

**Response:**
```json
{
  "document_id": 1,
  "filename": "return_policy.pdf",
  "chunk_count": 12,
  "message": "Document uploaded and indexed successfully. 12 chunks stored."
}
```

**Errors:**
| Status | Cause |
|--------|-------|
| `422`  | Unsupported file type, empty file, or no extractable text |
| `413`  | File exceeds 10 MB |
| `503`  | Embedding service unavailable (`OPENAI_API_KEY` not set or OpenAI error) |

---

### `POST /chat`

Send a message and optionally use the document knowledge base.

**Request:**
```json
{
  "user_message": "What is the return policy?",
  "conversation_id": "3f2a1b4c-...",
  "document_context": true
}
```

- `user_message` — required, 1–4000 characters
- `conversation_id` — optional (max 100 chars). Omit to start a new conversation.
- `document_context` — optional boolean (default `false`). Set `true` to search uploaded documents.

**Response:**
```json
{
  "conversation_id": "3f2a1b4c-...",
  "user_message": "What is the return policy?",
  "assistant_response": "According to the policy document, returns are accepted within 30 days...",
  "sources": [
    "return_policy.pdf (chunk 0)",
    "return_policy.pdf (chunk 3)"
  ]
}
```

- `sources` — populated only when `document_context=true`. Empty list otherwise.

**Errors:**
| Status | Cause |
|--------|-------|
| `422`  | Validation error (empty message, message too long, etc.) |
| `503`  | LLM or vector store unavailable |

---

### `GET /chat/conversations/{conversation_id}`

Retrieve the full message history for a conversation.

**Response:**
```json
{
  "conversation_id": "3f2a1b4c-...",
  "messages": [
    {"id": 1, "role": "user",      "content": "What is your return policy?", "created_at": "..."},
    {"id": 2, "role": "assistant", "content": "Returns are accepted within 30 days...", "created_at": "..."}
  ]
}
```

---

### `GET /health`

```json
{"status": "ok", "version": "2.0.0"}
```

---

## Demo Flow

```bash
# 1. Upload a document
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@return_policy.txt"

# → {"document_id": 1, "filename": "return_policy.txt", "chunk_count": 8, ...}

# 2. Ask a question using the document
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_message": "What is your return policy?", "document_context": true}'

# → {
#     "conversation_id": "abc-123...",
#     "assistant_response": "According to the policy, returns are accepted within 30 days...",
#     "sources": ["return_policy.txt (chunk 0)", "return_policy.txt (chunk 2)"]
#   }

# 3. Continue the conversation
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "abc-123...", "user_message": "What about refunds?", "document_context": true}'
```

---

## Quickstart

### Docker (recommended)

```bash
git clone https://github.com/Arcan17/ai-support-bot.git
cd ai-support-bot
cp .env.example .env
# Edit .env — set your OPENAI_API_KEY
docker-compose up --build
```

API: `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`

### Local

```bash
git clone https://github.com/Arcan17/ai-support-bot.git
cd ai-support-bot

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env — set your OPENAI_API_KEY

uvicorn app.main:app --reload
```

---

## Environment Variables

| Variable         | Description                                      | Default                       |
|------------------|--------------------------------------------------|-------------------------------|
| `OPENAI_API_KEY` | Your OpenAI key — required for `/chat` and RAG   | *(required)*                  |
| `OPENAI_MODEL`   | Chat model                                       | `gpt-4o-mini`                 |
| `DATABASE_URL`   | SQLAlchemy connection string                     | `sqlite:///./support_bot.db`  |
| `CHROMA_PATH`    | ChromaDB persistence directory                   | `./chroma_db`                 |
| `DEBUG`          | Enable debug mode                                | `false`                       |

> The app starts without a key. Calling `/chat` or `/documents/upload` without one returns HTTP 503 with a clear message — no crash, no stack trace.

---

## Running Tests

All OpenAI and ChromaDB calls are mocked — no API key or internet connection needed.

```bash
pytest tests/ -v
```

```
tests/test_chat.py          17 passed   ← happy path, validation, LLM errors
tests/test_chat_rag.py      16 passed   ← RAG mode, sources, vector store errors
tests/test_conversations.py  7 passed   ← GET history, multi-turn, 404
tests/test_documents.py     15 passed   ← upload .txt/.pdf/.csv, validation, 503
tests/test_health.py         3 passed   ← liveness probe
──────────────────────────────────────────────────────────
58 passed in 0.27s
```

---

## Architecture

```
ai-support-bot/
├── app/
│   ├── main.py                    # FastAPI app, lifespan, /health
│   ├── config.py                  # pydantic-settings — env vars
│   ├── database.py                # SQLAlchemy engine, session, Base
│   ├── models.py                  # Message + Document ORM models
│   ├── schemas.py                 # Pydantic v2 schemas with validation
│   ├── routers/
│   │   ├── chat.py                # POST /chat (with RAG), GET /chat/conversations/{id}
│   │   └── documents.py           # POST /documents/upload
│   └── services/
│       ├── llm_service.py         # ChatOpenAI — get_ai_response(context=...)
│       ├── document_service.py    # text extraction (txt/pdf/csv) + chunking
│       └── vector_store.py        # ChromaDB — add_chunks(), search()
├── tests/
│   ├── conftest.py                # in-memory DB + mocked LLM, search, add_chunks
│   ├── test_chat.py
│   ├── test_chat_rag.py
│   ├── test_conversations.py
│   ├── test_documents.py
│   └── test_health.py
├── .github/workflows/ci.yml
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── pytest.ini
```

---

## Tech Stack

| Layer          | Technology                               |
|----------------|------------------------------------------|
| API            | FastAPI 0.115 (async)                    |
| LLM            | LangChain 0.3 + ChatOpenAI               |
| AI model       | OpenAI GPT-4o-mini                       |
| Embeddings     | OpenAI text-embedding-3-small            |
| Vector store   | ChromaDB 0.5 (local persistence)         |
| Text splitting | LangChain RecursiveCharacterTextSplitter |
| PDF parsing    | pypdf 4.3                                |
| Database       | SQLite via SQLAlchemy 2.0                |
| Validation     | Pydantic v2                              |
| Testing        | pytest + AsyncMock                       |
| Container      | Docker + Docker Compose                  |
| CI/CD          | GitHub Actions                           |

---

## Technical Decisions

**Why ChromaDB?**  
Zero-config local persistence. No external service required — the vector store lives in `./chroma_db/`. Trivially replaceable with Pinecone or Weaviate by swapping `vector_store.py`.

**Why `text-embedding-3-small` and not `ada-002`?**  
`text-embedding-3-small` is cheaper, faster, and outperforms `ada-002` on most retrieval benchmarks. Same API, same code.

**Why inject context into the system prompt instead of as a separate message?**  
The system message is the canonical place for instructions and context. Injecting there keeps the human/assistant turn structure clean, which helps the LLM stay in the assistant role.

**Why store document metadata in SQLite separately from ChromaDB?**  
SQLite tracks which documents exist, their filenames, and chunk counts. ChromaDB stores vectors and text. Separating concerns means you can list or delete documents from a normal SQL query without touching the vector store.

---

## Freelance Use Cases

| Use case | What you configure |
|---|---|
| **Customer support bot** | Deploy as-is with a custom system prompt |
| **FAQ assistant** | Upload FAQ PDF → users chat with it |
| **HR policy assistant** | Upload employee handbook → answer policy questions |
| **Lead capture assistant** | Add lead storage to the DB schema |
| **Document QA bot** | Upload any text, PDF, or CSV → instant question-answering |
| **Internal knowledge base bot** | Upload Notion exports, manuals, or runbooks |

---

## Roadmap

- [x] Multi-turn conversation memory (SQLite)
- [x] Input validation (min/max length, 422 on bad input)
- [x] LLM error handling — HTTP 503, no key leaks, server-side logs
- [x] RAG — document upload (.txt, .pdf, .csv) + ChromaDB retrieval
- [x] Sources returned in chat response
- [x] Full test suite with mocked LLM + embeddings (58 tests)
- [x] Docker ready
- [x] CI/CD — GitHub Actions
- [ ] `GET /documents` — list uploaded documents
- [ ] `DELETE /documents/{id}` — remove a document and its chunks
- [ ] `/conversations` list endpoint with pagination
- [ ] Streaming responses via Server-Sent Events
- [ ] WhatsApp integration (Twilio)
- [ ] Support multiple AI providers via env var (Claude, Gemini)

---

## License

MIT
