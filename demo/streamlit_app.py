"""
AI Support Bot — Streamlit demo UI.

Requires the FastAPI backend running at API_URL (default: http://localhost:8000).

Run:
    pip install streamlit httpx
    streamlit run demo/streamlit_app.py
"""

from __future__ import annotations

import os

import httpx
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="AI Support Bot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "indexed_docs" not in st.session_state:
    st.session_state.indexed_docs: list[str] = []

# ---------------------------------------------------------------------------
# Sidebar — document upload & settings
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("🤖 AI Support Bot")
    st.caption("FastAPI + LangChain + OpenAI + RAG")
    st.divider()

    # --- Health check ---
    try:
        health = httpx.get(f"{API_URL}/health", timeout=3.0)
        if health.status_code == 200:
            v = health.json().get("version", "?")
            st.success(f"API connected — v{v}")
        else:
            st.error("API returned an error")
    except Exception:
        st.error(f"Cannot reach API at {API_URL}")

    st.divider()

    # --- Document upload ---
    st.header("📄 Knowledge Base")

    uploaded_file = st.file_uploader(
        "Upload a document",
        type=["txt", "pdf", "csv"],
        help="Supported formats: .txt, .pdf, .csv — max 10 MB",
    )

    if uploaded_file is not None:
        if st.button("📤 Upload & Index", use_container_width=True, type="primary"):
            with st.spinner(f"Indexing {uploaded_file.name}…"):
                try:
                    resp = httpx.post(
                        f"{API_URL}/documents/upload",
                        files={
                            "file": (
                                uploaded_file.name,
                                uploaded_file.getvalue(),
                                uploaded_file.type or "application/octet-stream",
                            )
                        },
                        timeout=120.0,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        st.session_state.indexed_docs.append(data["filename"])
                        st.success(
                            f"✅ **{data['filename']}** indexed — {data['chunk_count']} chunks"
                        )
                    else:
                        detail = resp.json().get("detail", "Unknown error")
                        st.error(f"Upload failed ({resp.status_code}): {detail}")
                except httpx.ConnectError:
                    st.error(f"Cannot connect to API at {API_URL}")
                except Exception as exc:
                    st.error(f"Unexpected error: {exc}")

    if st.session_state.indexed_docs:
        st.markdown("**Indexed documents:**")
        for doc in st.session_state.indexed_docs:
            st.markdown(f"- 📖 `{doc}`")

    st.divider()

    # --- Chat settings ---
    st.header("⚙️ Settings")

    use_rag = st.toggle(
        "Use document context",
        value=bool(st.session_state.indexed_docs),
        help="Query the knowledge base before answering. Requires at least one indexed document.",
    )

    if st.button("🗑️ New conversation", use_container_width=True):
        st.session_state.conversation_id = None
        st.session_state.messages = []
        st.rerun()

    if st.session_state.conversation_id:
        st.caption(f"Conversation: `{st.session_state.conversation_id[:8]}…`")

# ---------------------------------------------------------------------------
# Main — chat interface
# ---------------------------------------------------------------------------

st.header("💬 Chat")

# Display conversation history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander("📎 Sources used", expanded=False):
                for src in msg["sources"]:
                    st.markdown(f"- `{src}`")

# Chat input
if prompt := st.chat_input("Ask a question…"):
    # Show user message immediately
    st.session_state.messages.append({"role": "user", "content": prompt, "sources": []})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Call the API
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                payload: dict = {
                    "user_message": prompt,
                    "document_context": use_rag,
                }
                if st.session_state.conversation_id:
                    payload["conversation_id"] = st.session_state.conversation_id

                resp = httpx.post(
                    f"{API_URL}/chat",
                    json=payload,
                    timeout=60.0,
                )

                if resp.status_code == 200:
                    data = resp.json()
                    st.session_state.conversation_id = data["conversation_id"]
                    reply = data["assistant_response"]
                    sources = data.get("sources", [])

                    st.markdown(reply)
                    if sources:
                        with st.expander("📎 Sources used", expanded=True):
                            for src in sources:
                                st.markdown(f"- `{src}`")

                    st.session_state.messages.append(
                        {"role": "assistant", "content": reply, "sources": sources}
                    )

                elif resp.status_code == 503:
                    detail = resp.json().get("detail", "Service unavailable")
                    st.error(f"⚠️ {detail}")
                else:
                    detail = resp.json().get("detail", "Unknown error")
                    st.error(f"API error ({resp.status_code}): {detail}")

            except httpx.ConnectError:
                st.error(
                    f"Cannot connect to the API at **{API_URL}**. "
                    "Make sure the backend is running."
                )
            except Exception as exc:
                st.error(f"Unexpected error: {exc}")
