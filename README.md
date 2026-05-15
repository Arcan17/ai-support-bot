# AI Support Bot

**Customer support chatbot API built with FastAPI + LangChain + OpenAI. Maintains full conversation history in SQLite.**

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-0.3-1C3C3C?style=flat)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991?style=flat&logo=openai&logoColor=white)
![Tests](https://img.shields.io/badge/tests-20%20passing-brightgreen?style=flat)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat&logo=docker&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green?style=flat)

---

## What It Does

A production-ready REST API that powers a multi-turn AI chatbot. Each conversation is stored in SQLite so the bot remembers context across messages — like a real support agent would.

```
POST /chat          → send a message, get an AI reply
GET  /conversations/{id}  → retrieve full conversation history
GET  /health        → liveness probe
```

---

## How It Works

```
Client                  FastAPI                 OpenAI API
  │                        │                        │
  │── POST /chat ─────────▶│                        │
  │   {user_message,       │── load history ──────▶ DB
  │    conversation_id?}   │◀─ past messages ──────  │
  │                        │                        │
  │                        │── [system, history…, user_message] ──▶│
  │                        │◀─ assistant reply ─────────────────────│
  │                        │                        │
  │                        │── save user + reply ──▶ DB
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
  "conversation_id": "optional-uuid-to-continue"
}
```

**Response:**
```json
{
  "conversation_id": "3f2a1b4c-...",
  "user_message": "What is your return policy?",
  "assistant_response": "Our return policy allows returns within 30 days of purchase..."
}
```

---

### `GET /chat/conversations/{conversation_id}`

Retrieve the full message history for a conversation.

**Response:**
```json
{
  "conversation_id": "3f2a1b4c-...",
  "messages": [
    {"id": 1, "role": "user",      "content": "What is your return policy?", "created_at": "..."},
    {"id": 2, "role": "assistant", "content": "Our return policy...",         "created_at": "..."}
  ]
}
```

---

### `GET /health`

```json
{"status": "ok", "version": "1.0.0"}
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

API available at `http://localhost:8000`  
Docs at `http://localhost:8000/docs`

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

| Variable        | Description                          | Default         |
|-----------------|--------------------------------------|-----------------|
| `OPENAI_API_KEY`| Your OpenAI key (required)           | *(required)*    |
| `OPENAI_MODEL`  | Model to use                         | `gpt-4o-mini`   |
| `DATABASE_URL`  | SQLAlchemy connection string         | `sqlite:///./support_bot.db` |
| `DEBUG`         | Enable debug mode                    | `false`         |

---

## Running Tests

All OpenAI API calls are mocked with `unittest.mock.AsyncMock` — no API key or internet needed.

```bash
pytest tests/ -v
```

```
tests/test_health.py          3 passed   ← liveness probe
tests/test_chat.py            9 passed   ← POST /chat, history, LLM calls
tests/test_conversations.py   7 passed   ← GET history, multi-turn, 404
──────────────────────────────────────────────────────
19 passed in 0.4s
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
│   ├── schemas.py           # Pydantic request/response schemas
│   ├── routers/
│   │   └── chat.py          # POST /chat, GET /conversations/{id}
│   └── services/
│       └── llm_service.py   # LangChain ChatOpenAI — get_ai_response()
├── tests/
│   ├── conftest.py          # in-memory DB + mocked LLM fixtures
│   ├── test_health.py
│   ├── test_chat.py
│   └── test_conversations.py
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

---

## Technical Decisions

**Why LangChain instead of calling OpenAI directly?**  
LangChain's message abstractions (`HumanMessage`, `AIMessage`, `SystemMessage`) make it trivial to build structured conversation histories. More importantly, switching models (GPT-4o, Claude, Gemini) only requires changing one environment variable — the calling code stays identical.

**Why SQLite?**  
The access pattern is sequential: load history, call LLM, save messages. No concurrent writes. SQLite is zero-config and runs without any infrastructure. PostgreSQL can be swapped in by changing `DATABASE_URL`.

**Why UUID conversation IDs?**  
Client-controlled IDs mean any client can start a conversation and resume it later without a separate "create conversation" call.

---

## Roadmap

- [x] Multi-turn conversation memory (SQLite)
- [x] Full test suite with mocked LLM
- [x] Docker ready
- [ ] RAG — load a knowledge base (PDFs, docs) and answer questions from it
- [ ] `/conversations` list endpoint with pagination
- [ ] Streaming responses via Server-Sent Events
- [ ] WhatsApp integration (Twilio)
- [ ] Support multiple AI providers via env var (Claude, Gemini)

---

## License

MIT
