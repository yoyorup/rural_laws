"""Base fetcher with requests Session, retry logic, and common utilities."""

import logging
import time
from typing import Optional, Dict, Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import REQUEST_TIMEOUT, REQUEST_RETRY_TIMES, REQUEST_RETRY_BACKOFF, VERIFY_SSL

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
}


def build_session() -> requests.Session:
    """Create a requests Session with retry logic."""
    session = requests.Session()
    session.headers.update(HEADERS)

    retry = Retry(
        total=REQUEST_RETRY_TIMES,
        backoff_factor=REQUEST_RETRY_BACKOFF,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # 设置 SSL 验证
    session.verify = VERIFY_SSL

    return session


class BaseFetcher:
    """Base class for all fetchers."""

    def __init__(self):
        self.session = build_session()
        self.logger = logging.getLogger(self.__class__.__name__)

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: int = REQUEST_TIMEOUT,
        **kwargs,
    ) -> Optional[requests.Response]:
        """Perform a GET request with error handling."""
        try:
            resp = self.session.get(url, params=params, timeout=timeout, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.exceptions.Timeout:
            self.logger.warning(f"Timeout fetching {url}")
        except requests.exceptions.ConnectionError as e:
            self.logger.warning(f"Connection error fetching {url}: {e}")
        except requests.exceptions.HTTPError as e:
            self.logger.warning(f"HTTP error fetching {url}: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error fetching {url}: {e}")
        return None

    def post(
        self,
        url: str,
        data: Optional[Dict] = None,
        json: Optional[Dict] = None,
        timeout: int = REQUEST_TIMEOUT,
        **kwargs,
    ) -> Optional[requests.Response]:
        """Perform a POST request with error handling."""
        try:
            resp = self.session.post(url, data=data, json=json, timeout=timeout, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.exceptions.Timeout:
            self.logger.warning(f"Timeout posting to {url}")
        except requests.exceptions.HTTPError as e:
            self.logger.warning(f"HTTP error posting to {url}: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error posting to {url}: {e}")
        return None

    def polite_sleep(self, seconds: float = 1.0) -> None:
        """Sleep to be polite to servers."""
        time.sleep(seconds)
