"""Playwright browser fetcher wrapper."""

from __future__ import annotations

from dataclasses import dataclass


class BrowserFetchError(RuntimeError):
    """Raised when browser rendering fails."""


@dataclass(slots=True)
class BrowserFetcher:
    """Small wrapper around Playwright for explicit browser fallback."""

    timeout_milliseconds: int = 30_000
    headless: bool = True

    async def fetch_text(self, url: str) -> str:
        """Render a URL in Chromium and return page HTML."""

        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise BrowserFetchError(
                "Playwright is installed as a dependency but browser support is unavailable."
            ) from exc

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=self.headless)
            page = await browser.new_page()
            page.set_default_timeout(self.timeout_milliseconds)
            try:
                await page.goto(url, wait_until="networkidle")
                return await page.content()
            except Exception as exc:
                raise BrowserFetchError(f"Browser fetch failed for {url}: {exc}") from exc
            finally:
                await browser.close()
