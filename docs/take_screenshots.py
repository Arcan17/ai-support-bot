"""
Screenshot automation for AI Support Bot README.
Requires: playwright (pip install playwright && playwright install chromium)
Requires:
  - FastAPI running on localhost:8002  (uvicorn app.main:app --port 8002)
  - Streamlit running:  API_URL=http://localhost:8002 streamlit run demo/streamlit_app.py --server.port 8503
  - Real OPENAI_API_KEY in .env (needed for document-upload and chat-with-rag)

Usage:
  python3 docs/take_screenshots.py
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
STREAMLIT_URL   = "http://localhost:8503"
API_DOCS_URL    = "http://localhost:8002/docs"

VIEWPORT = {"width": 1400, "height": 860}


async def main():
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport=VIEWPORT)

        # ── 1. chat-empty.png ─────────────────────────────────────────────
        print("→ chat-empty.png …")
        page = await ctx.new_page()
        await page.goto(STREAMLIT_URL, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2500)
        await page.screenshot(
            path=str(SCREENSHOTS_DIR / "chat-empty.png"), full_page=False)
        print("  ✅ saved chat-empty.png")

        # ── 2. document-upload.png  (needs real OPENAI_API_KEY) ──────────
        print("→ document-upload.png  (requires real OpenAI key) …")
        faq_btn = page.get_by_role("button", name="Load sample FAQ")
        await faq_btn.click()
        await page.wait_for_timeout(4000)

        # Check if upload succeeded or failed
        error_visible = await page.locator("text=Upload failed").is_visible()
        if error_visible:
            print("  ⚠️  Upload failed — no real OpenAI key. Skipping RAG screenshots.")
            print("     Set OPENAI_API_KEY in .env and re-run for full screenshots.")
        else:
            await page.wait_for_selector("text=Document indexed", timeout=25000)
            await page.wait_for_timeout(800)
            await page.screenshot(
                path=str(SCREENSHOTS_DIR / "document-upload.png"), full_page=False)
            print("  ✅ saved document-upload.png")

            # ── 3. chat-with-rag.png ──────────────────────────────────────
            print("→ chat-with-rag.png  (calling OpenAI — ~10 s) …")
            # Toggle should be auto-enabled; verify
            toggle_input = page.locator('input[type="checkbox"]').first
            if not await toggle_input.is_checked():
                await page.locator("label", has_text="Use document context").click()
                await page.wait_for_timeout(500)

            chat_input = page.locator('textarea[placeholder="Ask a question…"]')
            await chat_input.fill("What is the return policy?")
            await chat_input.press("Enter")
            await page.wait_for_selector("text=Sources", timeout=45000)
            await page.wait_for_timeout(1200)
            await page.screenshot(
                path=str(SCREENSHOTS_DIR / "chat-with-rag.png"), full_page=False)
            print("  ✅ saved chat-with-rag.png")

        await page.close()

        # ── 4. api-docs.png  (no API key needed) ─────────────────────────
        print("→ api-docs.png …")
        page2 = await ctx.new_page()
        await page2.goto(API_DOCS_URL, wait_until="networkidle", timeout=20000)
        await page2.wait_for_timeout(2000)
        await page2.screenshot(
            path=str(SCREENSHOTS_DIR / "api-docs.png"), full_page=False)
        print("  ✅ saved api-docs.png")
        await page2.close()

        await browser.close()

    saved = [f.name for f in SCREENSHOTS_DIR.glob("*.png") if not f.name.startswith("_")]
    print(f"\n✅ Done — {len(saved)} screenshot(s) in docs/screenshots/: {saved}")


if __name__ == "__main__":
    asyncio.run(main())
