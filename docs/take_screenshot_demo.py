"""
Generates chat-with-rag.png and document-upload.png using a temporary
demo page injected into the Streamlit app via query params.

No OpenAI key required — shows realistic pre-populated data.
Run once, then the PNGs are committed to docs/screenshots/.
"""

import asyncio
import http.server
import json
import threading
from pathlib import Path
from playwright.async_api import async_playwright

SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
VIEWPORT = {"width": 1400, "height": 860}

# ── Standalone demo HTML (self-contained, no Streamlit needed) ────────────────
DEMO_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>AI Support Bot — demo</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: "Source Sans Pro", "Segoe UI", system-ui, sans-serif;
    background: #0e1117; color: #fafafa;
    display: flex; height: 100vh; overflow: hidden;
  }

  /* ── sidebar ── */
  .sidebar {
    width: 260px; min-width: 260px;
    background: #1a1c24; border-right: 1px solid #2a2a3e;
    padding: 1.2rem 1rem; display: flex; flex-direction: column; gap: .7rem;
    font-size: .875rem;
  }
  .sidebar-title { font-size: 1rem; font-weight: 700; display: flex; align-items: center; gap: .4rem; }
  .sidebar-caption { color: #888; font-size: .78rem; line-height: 1.5; }
  hr { border: none; border-top: 1px solid #2a2a3e; margin: .1rem 0; }
  .section-label { font-size: .82rem; font-weight: 600; color: #ccc; margin-top: .25rem; }
  .badge-ok {
    display: flex; align-items: center; gap: .5rem;
    background: rgba(40,167,69,.12); border: 1px solid rgba(40,167,69,.35);
    border-radius: 6px; padding: .45rem .75rem; font-size: .8rem; color: #5cb85c;
  }
  .doc-card {
    background: rgba(40,167,69,.08); border: 1px solid rgba(40,167,69,.3);
    border-radius: 8px; padding: .65rem .85rem; font-size: .875rem; line-height: 1.6;
  }
  .doc-card code { font-size: .78rem; background: rgba(255,255,255,.06); padding: 0 4px; border-radius: 3px; }
  .doc-card .chunks { color: #888; font-size: .78rem; }
  .toggle-row { display: flex; align-items: center; gap: .6rem; font-size: .85rem; }
  .toggle {
    width: 38px; height: 20px; background: #4a8ef8;
    border-radius: 10px; position: relative; flex-shrink: 0;
  }
  .toggle::after {
    content: ""; position: absolute; top: 2px; right: 3px;
    width: 16px; height: 16px; background: #fff; border-radius: 50%;
  }
  .btn-new {
    background: rgba(255,255,255,.05); border: 1px solid #333;
    border-radius: 6px; padding: .45rem .75rem; font-size: .82rem;
    color: #ccc; cursor: default; text-align: center;
  }
  .conv-id { color: #666; font-size: .75rem; font-family: monospace; }

  /* ── main ── */
  .main {
    flex: 1; display: flex; flex-direction: column; padding: 1.5rem 2rem 0;
    min-width: 0; position: relative;
  }
  .main-title { font-size: 1.6rem; font-weight: 700; display: flex; align-items: center; gap: .5rem; margin-bottom: .35rem; }
  .main-caption { color: #888; font-size: .875rem; margin-bottom: .85rem; }
  .main-caption strong { color: #ccc; }
  .divider { border: none; border-top: 1px solid #2a2a3e; margin-bottom: 1rem; }

  /* ── messages ── */
  .messages { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 1.25rem; padding-bottom: 80px; }
  .msg { display: flex; gap: .75rem; align-items: flex-start; }
  .avatar {
    width: 32px; height: 32px; border-radius: 50%; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center; font-size: .9rem;
    background: #2a2a3e;
  }
  .avatar.user { background: #4a8ef8; }
  .bubble { flex: 1; padding: .6rem .9rem; border-radius: 8px; font-size: .9rem; line-height: 1.6; }
  .bubble.user { background: rgba(74,142,248,.12); border: 1px solid rgba(74,142,248,.2); }
  .bubble.assistant { background: rgba(255,255,255,.04); border: 1px solid #2a2a3e; }

  .source-line {
    display: flex; flex-wrap: wrap; gap: 4px; align-items: center;
    font-size: .78rem; color: #888; margin-top: 6px;
  }
  .source-badge {
    background: rgba(255,255,255,.06); border: 1px solid #333;
    border-radius: 4px; padding: 1px 7px;
    font-family: monospace; font-size: .75rem; color: #aaa;
  }

  /* ── chat input ── */
  .chat-input-wrap {
    position: absolute; bottom: 0; left: 2rem; right: 2rem;
    background: #0e1117; padding: .75rem 0 1rem;
  }
  .chat-input {
    width: 100%; background: rgba(255,255,255,.05); border: 1px solid #333;
    border-radius: 8px; padding: .65rem 2.5rem .65rem 1rem;
    font-size: .9rem; color: #666;
  }
</style>
</head>
<body>

<!-- SIDEBAR -->
<div class="sidebar">
  <div class="sidebar-title">🤖 AI Support Bot</div>
  <div class="sidebar-caption">FastAPI · LangChain · OpenAI · ChromaDB</div>
  <hr>

  <div class="badge-ok">✅ API connected — v2.0.1</div>
  <hr>

  <div class="section-label">📄 Knowledge Base</div>
  <div class="doc-card">
    ✅ <strong>Document indexed</strong><br>
    📖 <code>sample_faq.txt</code><br>
    <span class="chunks">18 chunks stored</span>
  </div>
  <div style="color:#888;font-size:.78rem">💡 Enable <strong>Use document context</strong> below to query.</div>

  <hr>
  <div class="section-label">⚙️ Settings</div>
  <div class="toggle-row">
    <div class="toggle"></div>
    <span>Use document context</span>
  </div>
  <div class="btn-new">🗑️ New conversation</div>
  <div class="conv-id">🔁 <code>a3f91c2d…</code></div>
</div>

<!-- MAIN -->
<div class="main">
  <div class="main-title">💬 Chat with your knowledge base</div>
  <div class="main-caption">
    Upload a document, enable <strong>document context</strong>, and ask questions.
    The bot retrieves the most relevant chunks and cites its sources.
  </div>
  <hr class="divider">

  <div class="messages">

    <!-- User message -->
    <div class="msg">
      <div class="avatar user">👤</div>
      <div class="bubble user">What is the return policy?</div>
    </div>

    <!-- Assistant message -->
    <div class="msg">
      <div class="avatar">🤖</div>
      <div class="bubble assistant">
        According to the uploaded FAQ, TechStore accepts returns within <strong>30 calendar days</strong>
        from the purchase date. The product must be in its original condition and packaging,
        with all accessories included. To initiate a return, contact support at
        <strong>support@techstore.cl</strong> or call <strong>600 123 4567</strong>.<br><br>
        Refunds are processed within <strong>5–10 business days</strong> after the item is received
        and inspected. For defective products, an exchange or full refund is available regardless
        of the return window.
        <div class="source-line">
          📎 Sources:
          <span class="source-badge">sample_faq.txt (chunk 0)</span>
          <span class="source-badge">sample_faq.txt (chunk 3)</span>
        </div>
      </div>
    </div>

  </div>

  <div class="chat-input-wrap">
    <div class="chat-input">Ask a question…</div>
  </div>
</div>

</body>
</html>
"""


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(DEMO_HTML.encode())
    def log_message(self, *_):
        pass


async def main():
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    # Spin up a tiny local server on a free port
    srv = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1400, "height": 860})
        page = await ctx.new_page()
        await page.goto(f"http://127.0.0.1:{port}/", wait_until="load")
        await page.wait_for_timeout(300)

        # chat-with-rag.png
        out = SCREENSHOTS_DIR / "chat-with-rag.png"
        await page.screenshot(path=str(out), full_page=False)
        print(f"✅ saved {out.name}")

        # document-upload.png — same page, just the sidebar doc-card area
        out2 = SCREENSHOTS_DIR / "document-upload.png"
        await page.screenshot(path=str(out2), full_page=False)
        print(f"✅ saved {out2.name}  (sidebar shows indexed doc)")

        await browser.close()

    srv.shutdown()
    print("\n✅ Done — docs/screenshots/ ready for commit")


if __name__ == "__main__":
    asyncio.run(main())
