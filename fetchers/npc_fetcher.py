"""Fetcher for 全国人大法律法规数据库 (flk.npc.gov.cn)."""

import hashlib
import json
import logging
import re
from datetime import datetime, timedelta
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from config import NPC_BASE_URL, NPC_SEARCH_API, NPC_SEARCH_KEYWORDS, NPC_DAYS_BACK
from database.models import Law
from fetchers.base_fetcher import BaseFetcher
from processors.text_cleaner import clean_html_text

logger = logging.getLogger(__name__)


class NpcFetcher(BaseFetcher):
    """
    Fetches rural-related laws from the National People's Congress
    Law and Regulation Database (flk.npc.gov.cn).
    """

    SEARCH_URL = "https://flk.npc.gov.cn/api/"
    DETAIL_BASE = "https://flk.npc.gov.cn"

    def fetch_recent_laws(self, days_back: int = NPC_DAYS_BACK) -> List[Law]:
        """Fetch laws published/revised within the last N days."""
        laws = []
        cutoff = datetime.now() - timedelta(days=days_back)

        for keyword in NPC_SEARCH_KEYWORDS:
            self.logger.info(f"Searching NPC for keyword: {keyword}")
            page_results = self._search_keyword(keyword, cutoff)
            laws.extend(page_results)
            self.polite_sleep(1.0)

        # Deduplicate by id
        seen = {}
        for law in laws:
            if law.id not in seen:
                seen[law.id] = law
        return list(seen.values())

    def _search_keyword(self, keyword: str, cutoff: datetime) -> List[Law]:
        """Search for laws by keyword and return list of Law objects."""
        laws = []
        page = 1
        page_size = 10

        while True:
            params = {
                "searchType": "title,summary",
                "sortTr": "f_bbrq_s desc",
                "page": page,
                "size": page_size,
                "rn": keyword,  # search query
            }

            resp = self.post(
                self.SEARCH_URL,
                json=params,
                headers={"Content-Type": "application/json"},
            )

            if resp is None:
                # Fallback: try GET-based search
                resp = self._fallback_search(keyword, page)
                if resp is None:
                    break

            try:
                data = resp.json()
            except (ValueError, AttributeError):
                self.logger.warning(f"Failed to parse JSON for keyword={keyword} page={page}")
                break

            items = data.get("result", {}).get("data", []) if isinstance(data, dict) else []
            if not items:
                break

            for item in items:
                publish_date_str = item.get("f_bbrq_s", "") or item.get("f_fbrq_s", "")
                if publish_date_str:
                    try:
                        pub_dt = datetime.strptime(publish_date_str[:10], "%Y-%m-%d")
                        if pub_dt < cutoff:
                            return laws  # results are sorted desc, stop early
                    except ValueError:
                        pass

                law = self._item_to_law(item)
                if law:
                    laws.append(law)

            if len(items) < page_size:
                break
            page += 1
            self.polite_sleep(0.5)

        return laws

    def _fallback_search(self, keyword: str, page: int) -> Optional[object]:
        """Fallback GET search against NPC website."""
        url = f"https://flk.npc.gov.cn/fl.html"
        params = {"keyword": keyword, "page": page}
        return self.get(url, params=params)

    def _item_to_law(self, item: dict) -> Optional[Law]:
        """Convert an API result item to a Law dataclass."""
        title = item.get("title", "").strip()
        if not title:
            return None

        detail_url = item.get("url", "") or ""
        if detail_url and not detail_url.startswith("http"):
            detail_url = urljoin(self.DETAIL_BASE, detail_url)

        if not detail_url:
            # build URL from id
            law_id_field = item.get("id", "")
            if law_id_field:
                detail_url = f"{self.DETAIL_BASE}/flsearch/detail?id={law_id_field}"

        law_hash = hashlib.md5(detail_url.encode()).hexdigest() if detail_url else \
                   hashlib.md5(title.encode()).hexdigest()

        publish_date = (item.get("f_bbrq_s", "") or item.get("f_fbrq_s", "") or "")[:10]
        effective_date = (item.get("f_sxrq_s", "") or "")[:10]

        # Fetch full text if URL is available
        raw_text = item.get("summary", "") or ""
        if detail_url and len(raw_text) < 200:
            raw_text = self._fetch_full_text(detail_url) or raw_text

        return Law(
            id=law_hash,
            title=title,
            source="npc",
            source_url=detail_url,
            publish_date=publish_date or None,
            effective_date=effective_date or None,
            content_hash=hashlib.md5(raw_text.encode()).hexdigest(),
            raw_text=raw_text,
        )

    def _fetch_full_text(self, url: str) -> Optional[str]:
        """Fetch and extract the full text of a law from its detail page."""
        self.logger.info(f"Fetching full text: {url}")
        resp = self.get(url)
        if resp is None:
            return None

        try:
            resp.encoding = resp.apparent_encoding or "utf-8"
            soup = BeautifulSoup(resp.text, "lxml")

            # Try common content selectors for NPC pages
            for selector in [
                ".law-content", "#lawContent", ".content", ".article-content",
                "article", ".main-content", "#content",
            ]:
                elem = soup.select_one(selector)
                if elem:
                    return clean_html_text(str(elem))

            # Fallback: get all paragraph text
            paragraphs = soup.find_all(["p", "div"], class_=re.compile(r"content|article|law"))
            if paragraphs:
                return clean_html_text(" ".join(p.get_text() for p in paragraphs))

            # Last resort: body text
            body = soup.find("body")
            return clean_html_text(body.get_text()) if body else None
        except Exception as e:
            self.logger.error(f"Error parsing law detail page {url}: {e}")
            return None
