# AI Support Bot

**Customer support chatbot API built with FastAPI + LangChain + OpenAI. Maintains full conversation history in SQLite.**

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-0.3-1C3C3C?style=flat)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991?style=flat&logo=openai&logoColor=white)
![Tests](https://img.shields.io/badge/tests-27%20passing-brightgreen?style=flat)
![CI](https://img.shields.io/github/actions/workflow/status/Arcan17/ai-support-bot/ci.yml?label=CI&logo=github)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat&logo=docker&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green?style=flat)

---

## Current Scope

This is **v1.0.0** — a fully functional chatbot API with:

- Multi-turn conversation memory persisted in SQLite
- Input validation (min/max length, clean error messages)
- Graceful error handling — LLM failures return HTTP 503 without leaking keys or stack traces
- 27 passing tests (all LLM calls mocked — no API key needed to run them)
- Docker ready, CI on every push

What's **not** in this version (planned for v2):
- RAG — answering questions from a knowledge base (PDFs, docs)
- WhatsApp / Twilio integration

---

## What It Does

A production-ready REST API that powers a multi-turn AI chatbot. Each conversation is stored in SQLite so the bot remembers context across messages — like a real support agent would.

```
POST /chat                                  → send a message, get an AI reply
GET  /chat/conversations/{conversation_id}  → retrieve full conversation history
GET  /health                                → liveness probe
```

---

## How It Works

```
Client                  FastAPI                 OpenAI API
  │                        │                        │
  │── POST /chat ─────────▶│                        │
  │   {user_message,       │── load history ───────▶ DB
  │    conversation_id?}   │◀─ past messages ───────  │
  │                        │                        │
  │                        │── [system, history…, user_message] ──▶│
  │                        │◀─ assistant reply ─────────────────────│
  │                        │                        │
  │                        │── save user + reply ───▶ DB
  │◀─ {conversation_id,    │                        │
  │    assistant_response} │                        │
```

---

## Endpoints

### `POST /chat`

Start a new conversation or continue an existing one.

**Request:**
```json
{
  "user_message": "What is your return policy?",
  "conversation_id": "3f2a1b4c-8e1a-4b2c-9d3e-5f6a7b8c9d0e"
}
```

- `user_message` — required, 1–4000 characters
- `conversation_id` — optional (max 100 chars). Omit to start a new conversation.

**Response:**
```json
{
  "conversation_id": "3f2a1b4c-8e1a-4b2c-9d3e-5f6a7b8c9d0e",
  "user_message": "What is your return policy?",
  "assistant_response": "Our return policy allows returns within 30 days of purchase..."
}
```

**Errors:**
| Status | Cause |
|--------|-------|
| `422`  | Validation error (empty message, message too long, etc.) |
| `503`  | LLM unavailable or `OPENAI_API_KEY` not configured |

---

### `GET /chat/conversations/{conversation_id}`

Retrieve the full message history for a conversation.

**Response:**
```json
{
  "conversation_id": "3f2a1b4c-8e1a-4b2c-9d3e-5f6a7b8c9d0e",
  "messages": [
    {"id": 1, "role": "user",      "content": "What is your return policy?", "created_at": "..."},
    {"id": 2, "role": "assistant", "content": "Our return policy...",         "created_at": "..."}
  ]
}
```

**Errors:** `404` if the conversation ID doesn't exist.

---

### `GET /health`

```json
{"status": "ok", "version": "1.0.0"}
```

---

## Freelance Use Cases

The same architecture adapts directly to client projects:

| Use case | What changes |
|---|---|
| **Customer support bot** | Deploy as-is with a custom system prompt |
| **FAQ assistant** | Feed a product FAQ as context in the system prompt |
| **Lead capture assistant** | Add lead storage to the DB schema |
| **Document-based support bot** | Add RAG layer (v2 roadmap) — bot answers from PDFs/docs |
| **Internal helpdesk bot** | Connect to Notion/Confluence via MCP for context |

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

API available at `http://localhost:8000`  
Interactive docs at `http://localhost:8000/docs`

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

| Variable         | Description                                      | Default       |
|------------------|--------------------------------------------------|---------------|
| `OPENAI_API_KEY` | Your OpenAI key — required for `/chat`           | *(required)*  |
| `OPENAI_MODEL`   | Model to use                                     | `gpt-4o-mini` |
| `DATABASE_URL`   | SQLAlchemy connection string                     | `sqlite:///./support_bot.db` |
| `DEBUG`          | Enable debug mode                                | `false`       |

> The app starts without a key. Calling `/chat` without one returns HTTP 503 with a clear message — no crash, no stack trace.

---

## Running Tests

All OpenAI API calls are mocked with `unittest.mock.AsyncMock` — no API key or internet connection needed.

```bash
pytest tests/ -v
```

```
tests/test_chat.py           17 passed   ← happy path, validation, LLM errors
tests/test_conversations.py   7 passed   ← GET history, multi-turn, 404
tests/test_health.py          3 passed   ← liveness probe
─────────────────────────────────────────
27 passed in 0.15s
```

---

## Architecture

```
ai-support-bot/
├── app/
│   ├── main.py              # FastAPI app, lifespan, /health
│   ├── config.py            # pydantic-settings — env vars
│   ├── database.py          # SQLAlchemy engine, session, Base
│   ├── models.py            # Message ORM model
│   ├── schemas.py           # Pydantic v2 schemas with validation
│   ├── routers/
│   │   └── chat.py          # POST /chat, GET /chat/conversations/{conversation_id}
│   └── services/
│       └── llm_service.py   # LangChain ChatOpenAI — get_ai_response(), LLMError
├── tests/
│   ├── conftest.py          # in-memory DB (StaticPool) + mocked LLM fixtures
│   ├── test_chat.py
│   ├── test_conversations.py
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

| Layer        | Technology                          |
|--------------|-------------------------------------|
| API          | FastAPI 0.115 (async)               |
| LLM          | LangChain 0.3 + ChatOpenAI          |
| AI model     | OpenAI GPT-4o-mini                  |
| Database     | SQLite via SQLAlchemy 2.0           |
| Validation   | Pydantic v2                         |
| Testing      | pytest + AsyncMock                  |
| Container    | Docker + Docker Compose             |
| CI/CD        | GitHub Actions                      |

---

## Technical Decisions

**Why LangChain instead of calling OpenAI directly?**  
LangChain's message abstractions (`HumanMessage`, `AIMessage`, `SystemMessage`) make it trivial to build structured conversation histories. More importantly, switching models (GPT-4o, Claude, Gemini) only requires changing one environment variable — the calling code stays identical.

**Why SQLite?**  
The access pattern is sequential: load history, call LLM, save messages. No concurrent writes. SQLite is zero-config and runs without any infrastructure. PostgreSQL can be swapped in by changing `DATABASE_URL`.

**Why UUID conversation IDs?**  
Client-controlled IDs mean any client can start a conversation and resume it later without a separate "create conversation" call.

**Why HTTP 503 for LLM errors?**  
503 ("Service Unavailable") is semantically correct — the API itself is running but a downstream dependency failed. The error message is deliberately vague to the client while the real cause is logged server-side, keeping stack traces and key names out of API responses.

---

## Roadmap

- [x] Multi-turn conversation memory (SQLite)
- [x] Input validation (min/max length, 422 on bad input)
- [x] LLM error handling — HTTP 503, no key leaks, server-side logs
- [x] Full test suite with mocked LLM (27 tests)
- [x] Docker ready
- [x] CI/CD — GitHub Actions
- [ ] RAG — load a knowledge base (PDFs, docs) and answer questions from it
- [ ] `/conversations` list endpoint with pagination
- [ ] Streaming responses via Server-Sent Events
- [ ] WhatsApp integration (Twilio)
- [ ] Support multiple AI providers via env var (Claude, Gemini)

---

## License

MIT
