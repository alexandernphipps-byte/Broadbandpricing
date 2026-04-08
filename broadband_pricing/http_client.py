"""Stealth HTTP client with anti-bot measures."""

import random
import time
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# Realistic browser User-Agent strings
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
]


def get_browser_headers(referer: Optional[str] = None) -> dict:
    """Get realistic browser headers."""
    ua = random.choice(USER_AGENTS)
    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }
    if referer:
        headers["Referer"] = referer
        headers["Sec-Fetch-Site"] = "same-origin"
    return headers


def get_api_headers(referer: Optional[str] = None) -> dict:
    """Get headers suitable for API/XHR requests."""
    ua = random.choice(USER_AGENTS)
    headers = {
        "User-Agent": ua,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/json",
        "DNT": "1",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }
    if referer:
        headers["Referer"] = referer
    return headers


class StealthSession:
    """HTTP session with anti-bot countermeasures."""

    def __init__(self, max_retries: int = 2, base_delay: float = 0.5):
        self.session = requests.Session()
        self.max_retries = max_retries
        self.base_delay = base_delay
        self._update_headers()

    def _update_headers(self):
        self.session.headers.update(get_browser_headers())

    def _random_delay(self, attempt: int = 0):
        """Add a random delay to appear more human."""
        delay = self.base_delay * (2**attempt) * 0.5 + random.uniform(0.2, 0.8)
        time.sleep(delay)

    def get(self, url: str, **kwargs) -> Optional[requests.Response]:
        """GET request with retries and anti-bot measures."""
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    self._random_delay(attempt)
                    self._update_headers()

                resp = self.session.get(url, timeout=10, **kwargs)

                if resp.status_code == 403:
                    logger.warning(f"403 Forbidden on {url}, attempt {attempt + 1}")
                    continue
                if resp.status_code == 429:
                    logger.warning(f"Rate limited on {url}, backing off")
                    self._random_delay(attempt + 1)
                    continue

                resp.raise_for_status()
                return resp

            except requests.RequestException as e:
                logger.warning(f"Request failed for {url}: {e}, attempt {attempt + 1}")
                if attempt == self.max_retries - 1:
                    return None

        return None

    def post(self, url: str, **kwargs) -> Optional[requests.Response]:
        """POST request with retries and anti-bot measures."""
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    self._random_delay(attempt)
                    self._update_headers()

                resp = self.session.post(url, timeout=10, **kwargs)

                if resp.status_code == 403:
                    logger.warning(f"403 Forbidden on {url}, attempt {attempt + 1}")
                    continue
                if resp.status_code == 429:
                    logger.warning(f"Rate limited on {url}, backing off")
                    self._random_delay(attempt + 1)
                    continue

                resp.raise_for_status()
                return resp

            except requests.RequestException as e:
                logger.warning(f"Request failed for {url}: {e}, attempt {attempt + 1}")
                if attempt == self.max_retries - 1:
                    return None

        return None

    def get_with_cloudscraper(self, url: str, **kwargs) -> Optional[requests.Response]:
        """Use cloudscraper to bypass Cloudflare protection."""
        try:
            import cloudscraper

            scraper = cloudscraper.create_scraper(
                browser={"browser": "chrome", "platform": "windows", "desktop": True}
            )
            resp = scraper.get(url, timeout=10, **kwargs)
            resp.raise_for_status()
            return resp
        except Exception as e:
            logger.warning(f"Cloudscraper failed for {url}: {e}")
            return None

    def get_with_playwright(self, url: str, wait_selector: Optional[str] = None) -> Optional[str]:
        """Use Playwright browser automation as a fallback."""
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent=random.choice(USER_AGENTS),
                )
                page = context.new_page()
                page.goto(url, wait_until="networkidle", timeout=10000)

                if wait_selector:
                    page.wait_for_selector(wait_selector, timeout=10000)

                content = page.content()
                browser.close()
                return content

        except ImportError:
            logger.warning("Playwright not installed. Install with: pip install playwright && playwright install chromium")
            return None
        except Exception as e:
            logger.warning(f"Playwright failed for {url}: {e}")
            return None
