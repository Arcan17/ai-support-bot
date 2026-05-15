"""
AI Support Bot — Streamlit demo UI.

Requires the FastAPI backend running at API_URL (default: http://localhost:8000).

Run:
    pip install streamlit httpx
    streamlit run demo/streamlit_app.py
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")
SAMPLE_FAQ_PATH = Path(__file__).parent.parent / "data" / "sample_faq.txt"

EXAMPLE_PROMPTS = [
    "What is the return policy?",
    "Summarize this document",
    "What services are available?",
    "What are the main requirements?",
]

# ---------------------------------------------------------------------------
# Page config & custom CSS
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="AI Support Bot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
/* Soften the sidebar divider */
[data-testid="stSidebar"] hr { margin: 0.6rem 0; }

/* Example prompt buttons — make them look like chips */
div[data-testid="stButton"] button[kind="secondary"] {
    border: 1px solid #333;
    background: rgba(255,255,255,0.03);
    text-align: left;
    font-size: 0.88rem;
}
div[data-testid="stButton"] button[kind="secondary"]:hover {
    border-color: #4a8ef8;
    background: rgba(74,142,248,0.08);
}

/* Source line under assistant messages */
.source-line {
    font-size: 0.78rem;
    color: #888;
    margin-top: 4px;
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    align-items: center;
}
.source-badge {
    background: rgba(255,255,255,0.06);
    border: 1px solid #333;
    border-radius: 4px;
    padding: 1px 7px;
    font-family: monospace;
    font-size: 0.75rem;
    color: #aaa;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------

defaults: dict = {
    "conversation_id": None,
    "messages": [],
    "indexed_docs": [],      # list[dict]: filename, chunk_count, document_id
    "pending_prompt": None,  # set by example-prompt buttons
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _upload_file(name: str, content: bytes, mime: str) -> dict | None:
    """POST /documents/upload. Returns the JSON body or shows an error."""
    try:
        resp = httpx.post(
            f"{API_URL}/documents/upload",
            files={"file": (name, content, mime)},
            timeout=120.0,
        )
        if resp.status_code == 200:
            return resp.json()
        st.error(f"Upload failed ({resp.status_code}): {resp.json().get('detail', 'Unknown error')}")
    except httpx.ConnectError:
        st.error(f"Cannot connect to the API at {API_URL}.")
    except Exception as exc:
        st.error(f"Unexpected error: {exc}")
    return None


def _chat(prompt: str, use_rag: bool) -> tuple[str, list[str]]:
    """POST /chat. Returns (reply, sources). Errors are returned as reply strings."""
    payload: dict = {
        "user_message": prompt,
        "document_context": use_rag,
    }
    if st.session_state.conversation_id:
        payload["conversation_id"] = st.session_state.conversation_id
    try:
        resp = httpx.post(f"{API_URL}/chat", json=payload, timeout=60.0)
        if resp.status_code == 200:
            data = resp.json()
            st.session_state.conversation_id = data["conversation_id"]
            return data["assistant_response"], data.get("sources", [])
        detail = resp.json().get("detail", "Unknown error")
        return f"⚠️ {detail}", []
    except httpx.ConnectError:
        return f"⚠️ Cannot connect to the API at {API_URL}.", []
    except Exception as exc:
        return f"⚠️ Unexpected error: {exc}", []


def _send(prompt: str, use_rag: bool) -> None:
    """Append user message, call API, append assistant message to session state."""
    st.session_state.messages.append({"role": "user", "content": prompt, "sources": []})
    reply, sources = _chat(prompt, use_rag)
    st.session_state.messages.append({"role": "assistant", "content": reply, "sources": sources})

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## 🤖 AI Support Bot")
    st.caption("FastAPI · LangChain · OpenAI · ChromaDB")
    st.divider()

    # --- API health ---
    try:
        health = httpx.get(f"{API_URL}/health", timeout=3.0)
        if health.status_code == 200:
            v = health.json().get("version", "?")
            st.success(f"API connected — v{v}", icon="✅")
        else:
            st.error("API returned an error")
    except Exception:
        st.error(f"Cannot reach API at {API_URL}")

    st.divider()
    st.markdown("### 📄 Knowledge Base")

    # --- Quick demo: load sample FAQ ---
    if SAMPLE_FAQ_PATH.exists():
        if st.button("⚡ Load sample FAQ", use_container_width=True,
                     help="Instantly indexes data/sample_faq.txt — great for a quick demo"):
            with st.spinner("Indexing sample FAQ…"):
                data = _upload_file("sample_faq.txt", SAMPLE_FAQ_PATH.read_bytes(), "text/plain")
            if data:
                st.session_state.indexed_docs.append({
                    "filename": data["filename"],
                    "chunk_count": data["chunk_count"],
                    "document_id": data["document_id"],
                })
                st.rerun()

    # --- Custom file upload ---
    uploaded_file = st.file_uploader(
        "Or upload your own",
        type=["txt", "pdf", "csv"],
        help="Supported: .txt · .pdf · .csv — max 10 MB",
    )
    if uploaded_file is not None:
        if st.button("📤 Upload & Index", use_container_width=True, type="primary"):
            with st.spinner(f"Indexing {uploaded_file.name}…"):
                data = _upload_file(
                    uploaded_file.name,
                    uploaded_file.getvalue(),
                    uploaded_file.type or "application/octet-stream",
                )
            if data:
                st.session_state.indexed_docs.append({
                    "filename": data["filename"],
                    "chunk_count": data["chunk_count"],
                    "document_id": data["document_id"],
                })
                st.rerun()

    # --- Indexed documents ---
    for doc in st.session_state.indexed_docs:
        st.markdown(
            f"""
<div style="
    background:rgba(40,167,69,0.08);
    border:1px solid rgba(40,167,69,0.3);
    border-radius:8px;
    padding:0.65rem 0.85rem;
    margin:0.5rem 0;
    font-size:0.875rem;
    line-height:1.6;
">
  ✅ <strong>Document indexed</strong><br>
  📖 <code style="font-size:0.8rem">{doc['filename']}</code><br>
  <span style="color:#888;font-size:0.78rem">{doc['chunk_count']} chunks stored</span>
</div>
""",
            unsafe_allow_html=True,
        )

    if st.session_state.indexed_docs:
        st.caption("💡 Enable **Use document context** below to query.")

    st.divider()
    st.markdown("### ⚙️ Settings")

    use_rag = st.toggle(
        "Use document context",
        value=bool(st.session_state.indexed_docs),
        help="Retrieve relevant document chunks before calling the LLM.",
    )

    if st.button("🗑️ New conversation", use_container_width=True):
        st.session_state.conversation_id = None
        st.session_state.messages = []
        st.session_state.pending_prompt = None
        st.rerun()

    if st.session_state.conversation_id:
        st.caption(f"🔁 `{st.session_state.conversation_id[:8]}…`")

# ---------------------------------------------------------------------------
# Main — header
# ---------------------------------------------------------------------------

st.markdown("## 💬 Chat with your knowledge base")
st.caption(
    "Upload a document, enable **document context**, and ask questions. "
    "The bot retrieves the most relevant chunks and cites its sources."
)
st.divider()

# ---------------------------------------------------------------------------
# Process pending prompt (from example buttons)
# ---------------------------------------------------------------------------

if st.session_state.pending_prompt:
    pending = st.session_state.pending_prompt
    st.session_state.pending_prompt = None
    with st.spinner("Thinking…"):
        _send(pending, use_rag)
    st.rerun()

# ---------------------------------------------------------------------------
# Chat display — empty state or message history
# ---------------------------------------------------------------------------

if not st.session_state.messages:
    # ── Empty state card ─────────────────────────────────────────────────
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown(
            """
<div style="
    border: 1px solid #2a2a3e;
    border-radius: 14px;
    padding: 2.25rem 2rem 1.75rem 2rem;
    text-align: center;
    background: rgba(255,255,255,0.02);
    margin: 1rem 0 1.5rem 0;
">
  <div style="font-size:2.75rem; margin-bottom:0.75rem;">🤖</div>
  <h4 style="margin:0 0 0.5rem 0; color:#e0e0e0; font-size:1.05rem;">
    Ready to answer questions
  </h4>
  <p style="color:#888; font-size:0.88rem; line-height:1.6; margin:0;">
    Upload a document, enable <strong>document context</strong>,<br>
    and ask questions about your knowledge base.
  </p>
</div>
""",
            unsafe_allow_html=True,
        )

        st.markdown(
            "<p style='text-align:center;color:#666;font-size:0.82rem;margin:0 0 0.5rem 0'>Try asking:</p>",
            unsafe_allow_html=True,
        )

        for prompt_text in EXAMPLE_PROMPTS:
            if st.button(prompt_text, use_container_width=True, key=f"ex__{prompt_text}"):
                st.session_state.pending_prompt = prompt_text
                st.rerun()

else:
    # ── Message history ───────────────────────────────────────────────────
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            sources = msg.get("sources", [])
            if sources:
                badges = "".join(
                    f'<span class="source-badge">{s}</span>' for s in sources
                )
                st.markdown(
                    f'<div class="source-line">📎 Sources: {badges}</div>',
                    unsafe_allow_html=True,
                )

# ---------------------------------------------------------------------------
# Chat input (always visible)
# ---------------------------------------------------------------------------

if prompt := st.chat_input("Ask a question…"):
    with st.spinner("Thinking…"):
        _send(prompt, use_rag)
    st.rerun()
