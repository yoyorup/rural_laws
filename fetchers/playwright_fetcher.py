"""Playwright-based fetcher for JavaScript-rendered pages."""

import asyncio
import logging
from typing import Optional, List
from pathlib import Path

from playwright.async_api import async_playwright, Browser, Page, Playwright

logger = logging.getLogger(__name__)


class PlaywrightFetcher:
    """Async Playwright wrapper for fetching JavaScript-rendered pages."""

    _instance: Optional["PlaywrightFetcher"] = None
    _playwright: Optional[Playwright] = None
    _browser: Optional[Browser] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def initialize(self):
        """Initialize Playwright and browser."""
        if self._playwright is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            logger.info("Playwright browser initialized")

    async def close(self):
        """Close browser and Playwright."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._browser = None
        self._playwright = None
        logger.info("Playwright browser closed")

    async def fetch_page(self, url: str, wait_for_selector: Optional[str] = None, timeout: int = 30000) -> Optional[str]:
        """
        Fetch a page and return its HTML content.

        Args:
            url: The URL to fetch
            wait_for_selector: Optional CSS selector to wait for
            timeout: Timeout in milliseconds

        Returns:
            HTML content or None if failed
        """
        if not self._browser:
            await self.initialize()

        page = await self._browser.new_page()

        try:
            # Set extra HTTP headers
            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            })

            # Navigate and wait for network to be idle
            await page.goto(url, wait_until="networkidle", timeout=timeout)

            # Wait for JavaScript to render content
            # If wait_for_selector is specified, wait for it
            if wait_for_selector:
                try:
                    await page.wait_for_selector(wait_for_selector, timeout=timeout)
                except Exception:
                    # If selector not found, continue anyway
                    pass

            # Additional wait for SPA apps to render
            await asyncio.sleep(3)

            # Check if there's an app element and wait for it to have content
            app_element = await page.query_selector("#app")
            if app_element:
                # Wait for the app to have meaningful content (not just empty div)
                await page.wait_for_function(
                    """() => {
                        const app = document.getElementById('app');
                        return app && app.innerText && app.innerText.length > 100;
                    }""",
                    timeout=timeout
                )

            # Wait a bit more for any dynamic content
            await asyncio.sleep(1)

            content = await page.content()
            return content

        except Exception as e:
            logger.warning(f"Error fetching {url}: {e}")
            # Try to get content anyway
            try:
                content = await page.content()
                if content and len(content) > 1000:
                    return content
            except:
                pass
            return None
        finally:
            await page.close()

    async def search_npc(self, keyword: str, timeout: int = 60000) -> Optional[str]:
        """
        Perform a search on NPC website and return the results page.

        Args:
            keyword: Search keyword
            timeout: Timeout in milliseconds

        Returns:
            HTML content or None if failed
        """
        if not self._browser:
            await self.initialize()

        page = await self._browser.new_page()

        try:
            # Set extra HTTP headers
            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            })

            # Go to the search page
            await page.goto("https://flk.npc.gov.cn/fl.html", wait_until="networkidle", timeout=timeout)

            # Wait for the search input to be ready
            await page.wait_for_selector(".el-input__inner", timeout=10000)

            # Type the keyword in the search input
            search_input = await page.query_selector(".el-input__inner")
            if search_input:
                await search_input.fill(keyword)
                await asyncio.sleep(0.5)

                # Press Enter to search
                await search_input.press("Enter")

                # Wait for results to load
                await asyncio.sleep(5)

            content = await page.content()
            return content

        except Exception as e:
            logger.warning(f"Error searching NPC for '{keyword}': {e}")
            # Try to get content anyway
            try:
                content = await page.content()
                if content and len(content) > 1000:
                    return content
            except:
                pass
            return None
        finally:
            await page.close()

    async def fetch_multiple(self, urls: List[str], max_concurrent: int = 3) -> dict:
        """
        Fetch multiple URLs concurrently.

        Args:
            urls: List of URLs to fetch
            max_concurrent: Maximum concurrent requests

        Returns:
            Dict mapping URL to HTML content
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_one(url: str) -> tuple:
            async with semaphore:
                content = await self.fetch_page(url)
                return url, content

        tasks = [fetch_one(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {url: content for url, content in results if not isinstance(content, Exception)}


# Synchronous wrapper
class SyncPlaywrightFetcher:
    """Synchronous wrapper for PlaywrightFetcher."""

    def __init__(self):
        self._async_fetcher = PlaywrightFetcher()

    def fetch_page(self, url: str, wait_for_selector: Optional[str] = None, timeout: int = 30000) -> Optional[str]:
        """Fetch a page synchronously."""
        try:
            return asyncio.run(self._async_fetcher.fetch_page(url, wait_for_selector, timeout))
        except Exception as e:
            logger.error(f"Error in sync fetch: {e}")
            return None

    def close(self):
        """Close the async fetcher."""
        if self._async_fetcher._browser:
            asyncio.run(self._async_fetcher.close())
