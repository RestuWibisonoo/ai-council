"""Local, visible Playwright bridge for filling prompts in official AI web UIs.

The bridge never reads cookies/tokens, bypasses login, or submits prompts.
The user logs in normally and explicitly sends each prompt.
"""
import asyncio
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, BrowserContext, Page, Playwright

from app.config import settings

PROVIDERS = {
    "chatgpt": {
        "label": "ChatGPT",
        "url": "https://chatgpt.com/",
        "selectors": [
            "#prompt-textarea",
            'div[contenteditable="true"][data-placeholder]',
            'div[contenteditable="true"][role="textbox"]',
            'textarea[placeholder]',
        ],
    },
    "gemini": {
        "label": "Gemini",
        "url": "https://gemini.google.com/app",
        "selectors": [
            "rich-textarea [contenteditable='true']",
            'div[contenteditable="true"][role="textbox"]',
            'textarea[placeholder]',
        ],
    },
    "claude": {
        "label": "Claude",
        "url": "https://claude.ai/new",
        "selectors": [
            'div[contenteditable="true"][data-placeholder]',
            'div[contenteditable="true"][role="textbox"]',
            'div[contenteditable="true"]',
            "textarea",
        ],
    },
    "notebooklm": {
        "label": "NotebookLM",
        "url": "https://notebooklm.google.com/",
        "selectors": [
            'textarea[placeholder]',
            'div[contenteditable="true"][role="textbox"]',
            'div[contenteditable="true"]',
        ],
    },
}


class PlaywrightBridge:
    def __init__(self) -> None:
        self._playwright: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._provider: Optional[str] = None
        self._lock = asyncio.Lock()

    async def _ensure_browser(self) -> BrowserContext:
        if self._context:
            try:
                if self._context.pages:
                    return self._context
            except Exception:
                self._context = None

        try:
            profile_dir = Path(settings.data_dir) / "playwright-profile"
            profile_dir.mkdir(parents=True, exist_ok=True)
            if self._playwright is None:
                self._playwright = await async_playwright().start()
            self._context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=False,
                args=["--no-first-run", "--no-default-browser-check"],
                viewport={"width": 1280, "height": 900},
            )
            self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
            return self._context
        except Exception as exc:
            message = str(exc)
            if "Executable doesn't exist" in message or "playwright install" in message.lower():
                raise RuntimeError(
                    "Chromium Playwright belum terpasang. Jalankan: "
                    "python -m playwright install chromium"
                ) from exc
            raise RuntimeError(
                "Browser Playwright gagal dibuka. Pastikan aplikasi dijalankan lokal "
                "dengan desktop/session grafis yang aktif."
            ) from exc

    async def open_and_fill(self, provider: str, prompt: str) -> dict:
        provider = provider.lower().strip()
        if provider not in PROVIDERS:
            raise ValueError("Provider tidak didukung. Pilih ChatGPT, Gemini, Claude, atau NotebookLM.")
        if not prompt.strip():
            raise ValueError("Prompt tidak boleh kosong.")
        if len(prompt) > 100_000:
            raise ValueError("Prompt terlalu panjang (maksimal 100.000 karakter).")

        async with self._lock:
            context = await self._ensure_browser()
            target = PROVIDERS[provider]
            page = self._page
            if page is None or page.is_closed():
                page = await context.new_page()
                self._page = page

            current_host = ""
            try:
                current_host = page.url.split("/")[2].lower()
            except Exception:
                pass
            target_host = target["url"].split("/")[2].lower()
            if current_host != target_host:
                await page.goto(target["url"], wait_until="domcontentloaded", timeout=45_000)
            await page.wait_for_timeout(900)

            editor = None
            for selector in target["selectors"]:
                locator = page.locator(selector)
                try:
                    count = min(await locator.count(), 8)
                    for index in range(count - 1, -1, -1):
                        candidate = locator.nth(index)
                        if await candidate.is_visible():
                            editor = candidate
                            break
                    if editor is not None:
                        break
                except Exception:
                    continue

            if editor is None:
                raise RuntimeError(
                    f"Kolom pesan {target['label']} belum ditemukan. Jika belum login, "
                    "silakan login manual di jendela browser, lalu klik tombol ini lagi."
                )

            try:
                await editor.fill(prompt, timeout=10_000)
            except Exception as exc:
                raise RuntimeError(
                    f"Prompt tidak berhasil dimasukkan ke {target['label']}. "
                    "Pastikan halaman siap dan kolom pesan terlihat."
                ) from exc

            self._provider = provider
            self._page = page
            return {
                "success": True,
                "provider": provider,
                "provider_label": target["label"],
                "message": "Prompt sudah dimasukkan. Periksa isi pesan dan klik Kirim sendiri.",
                "page_url": page.url,
                "submitted": False,
            }

    async def status(self) -> dict:
        active = self._context is not None and self._page is not None and not self._page.is_closed()
        return {
            "active": active,
            "provider": self._provider,
            "page_url": self._page.url if active and self._page else None,
            "profile_directory": "data/playwright-profile",
            "submitted_automatically": False,
        }

    async def close(self) -> dict:
        async with self._lock:
            if self._context:
                await self._context.close()
            if self._playwright:
                await self._playwright.stop()
            self._context = None
            self._playwright = None
            self._page = None
            self._provider = None
        return {"success": True, "message": "Jendela bridge ditutup."}


playwright_bridge = PlaywrightBridge()
