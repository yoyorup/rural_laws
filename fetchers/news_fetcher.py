"""Fetcher for related news from Xinhua, People's Daily, and Farmer's Daily."""

import logging
import re
from typing import List
from urllib.parse import urlencode, quote

from bs4 import BeautifulSoup

from database.models import NewsItem
from fetchers.base_fetcher import BaseFetcher
from processors.text_cleaner import clean_html_text

logger = logging.getLogger(__name__)

MAX_NEWS_PER_SOURCE = 5


class NewsFetcher(BaseFetcher):
    """Aggregate news related to a specific law from multiple Chinese news sources."""

    def fetch_news_for_law(self, law_id: str, law_title: str) -> List[NewsItem]:
        """Fetch news items related to a law by its title."""
        results: List[NewsItem] = []

        # Use a shortened title as query keyword (first 10-15 chars)
        keyword = law_title[:15].strip("（）()【】 ")

        sources = [
            ("xinhua", self._fetch_xinhua),
            ("farmer", self._fetch_farmer),
            ("people", self._fetch_people),
        ]

        for source_name, fetch_fn in sources:
            try:
                items = fetch_fn(law_id, keyword)
                results.extend(items[:MAX_NEWS_PER_SOURCE])
                self.polite_sleep(0.5)
            except Exception as e:
                self.logger.warning(f"Error fetching {source_name} news for '{keyword}': {e}")

        return results

    # ------------------------------------------------------------------
    # Xinhua News
    # ------------------------------------------------------------------

    def _fetch_xinhua(self, law_id: str, keyword: str) -> List[NewsItem]:
        url = f"http://so.news.cn/getNews"
        params = {
            "keyword": keyword,
            "curPage": 1,
            "pageSize": MAX_NEWS_PER_SOURCE,
            "sortField": "score",
            "searchFields": "1",
            "lang": "cn",
        }
        resp = self.get(url, params=params)
        if resp is None:
            return self._fetch_xinhua_html(law_id, keyword)

        try:
            data = resp.json()
            items = data.get("content", {}).get("results", []) if isinstance(data, dict) else []
            news = []
            for item in items[:MAX_NEWS_PER_SOURCE]:
                news.append(NewsItem(
                    law_id=law_id,
                    title=self._strip_tags(item.get("title", "")),
                    url=item.get("url", "") or item.get("sourceUrl", ""),
                    source="新华网",
                    published_at=item.get("pubTime", "")[:10] if item.get("pubTime") else None,
                    snippet=self._strip_tags(item.get("summary", ""))[:200],
                ))
            return news
        except (ValueError, KeyError):
            return self._fetch_xinhua_html(law_id, keyword)

    def _fetch_xinhua_html(self, law_id: str, keyword: str) -> List[NewsItem]:
        url = f"http://so.news.cn/?keyword={quote(keyword)}"
        resp = self.get(url)
        if resp is None:
            return []
        return self._parse_news_list(resp.text, law_id, "新华网", url)

    # ------------------------------------------------------------------
    # Farmer's Daily (农民日报)
    # ------------------------------------------------------------------

    def _fetch_farmer(self, law_id: str, keyword: str) -> List[NewsItem]:
        url = f"http://www.farmer.com.cn/search/index.htm"
        params = {"searchStr": keyword, "pageIndex": 1}
        resp = self.get(url, params=params)
        if resp is None:
            return []
        return self._parse_news_list(resp.text, law_id, "农民日报", url)

    # ------------------------------------------------------------------
    # People's Daily (人民日报)
    # ------------------------------------------------------------------

    def _fetch_people(self, law_id: str, keyword: str) -> List[NewsItem]:
        url = f"https://search.people.com.cn/s?keyword={quote(keyword)}&cl=1"
        resp = self.get(url)
        if resp is None:
            return []
        return self._parse_news_list(resp.text, law_id, "人民网", url)

    # ------------------------------------------------------------------
    # Generic HTML list parser
    # ------------------------------------------------------------------

    def _parse_news_list(
        self, html: str, law_id: str, source: str, base_url: str
    ) -> List[NewsItem]:
        """Generic parser for news listing pages."""
        try:
            soup = BeautifulSoup(html, "lxml")
            items = []

            # Try to find news links with dates
            for a in soup.find_all("a", href=True)[:30]:
                title = a.get_text(strip=True)
                href = a["href"]

                if len(title) < 8:  # skip short/navigation links
                    continue
                if not href.startswith("http"):
                    from urllib.parse import urljoin
                    href = urljoin(base_url, href)

                # Try to find nearby date text
                parent = a.parent
                date_text = parent.get_text() if parent else ""
                date_match = re.search(r"(\d{4}-\d{2}-\d{2})", date_text)
                pub_date = date_match.group(1) if date_match else None

                # Snippet: text in same container excluding the title
                snippet = ""
                if parent:
                    raw_snippet = parent.get_text(separator=" ", strip=True)
                    snippet = raw_snippet.replace(title, "").strip()[:200]

                items.append(NewsItem(
                    law_id=law_id,
                    title=title[:100],
                    url=href,
                    source=source,
                    published_at=pub_date,
                    snippet=snippet,
                ))

                if len(items) >= MAX_NEWS_PER_SOURCE:
                    break

            return items
        except Exception as e:
            self.logger.error(f"Error parsing news list HTML from {source}: {e}")
            return []

    @staticmethod
    def _strip_tags(text: str) -> str:
        return re.sub(r"<[^>]+>", "", text or "")
