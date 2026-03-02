"""Fetcher for 全国人大法律法规数据库 (flk.npc.gov.cn)."""

import hashlib
import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from config import NPC_BASE_URL, NPC_SEARCH_API, NPC_SEARCH_KEYWORDS, NPC_DAYS_BACK
from database.models import Law
from fetchers.base_fetcher import BaseFetcher
from fetchers.playwright_fetcher import PlaywrightFetcher
from processors.text_cleaner import clean_html_text

logger = logging.getLogger(__name__)


class NpcFetcher(BaseFetcher):
    """
    Fetches rural-related laws from the National People's Congress
    Law and Regulation Database (flk.npc.gov.cn).
    """

    SEARCH_URL = "https://flk.npc.gov.cn/api/"
    DETAIL_BASE = "https://flk.npc.gov.cn"
    WEB_SEARCH_URL = "https://flk.npc.gov.cn/fl.html"  # 网页搜索页面

    def __init__(self):
        super().__init__()
        self.playwright = PlaywrightFetcher()

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

        # 使用 Playwright 执行搜索
        html_content = asyncio.run(
            self.playwright.search_npc(keyword, timeout=60000)
        )

        if not html_content:
            self.logger.warning(f"Failed to search NPC for keyword={keyword}")
            return laws

        try:
            soup = BeautifulSoup(html_content, "lxml")
        except Exception as e:
            self.logger.warning(f"Failed to parse search results for keyword={keyword}: {e}")
            return laws

        # 解析搜索结果列表
        items = self._parse_search_results(soup)
        if not items:
            self.logger.warning(f"No search results found for keyword={keyword}")
            return laws

        for item in items:
            publish_date_str = item.get("date", "")
            if publish_date_str:
                try:
                    pub_dt = datetime.strptime(publish_date_str[:10], "%Y-%m-%d")
                    if pub_dt < cutoff:
                        break
                except ValueError:
                    pass

            law = self._item_to_law_from_web(item)
            if law:
                laws.append(law)

        return laws

    def _parse_search_results(self, soup: BeautifulSoup) -> List[dict]:
        """Parse search results from the web page."""
        items = []

        # 尝试多种选择器来匹配 NPC 网站的搜索结果
        # 搜索结果可能在不同的容器中
        result_containers = soup.select(
            ".search-result, .result-list, .list, ul.list, "
            ".el-table__body, .el-table__row, .result-item, "
            ".law-list, .law-item"
        )

        for container in result_containers:
            # 在每个容器中查找链接和日期
            links = container.find_all("a", href=True)

            for link in links:
                title = link.get_text(strip=True)
                href = link.get("href", "")

                # 过滤掉无效的标题
                if not title or len(title) < 5:
                    continue

                # 跳过非法规链接
                if any(x in href for x in ["javascript", "#", "mailto"]):
                    continue

                # 提取日期 - 在链接父元素或附近查找
                parent = link.parent
                date_str = ""
                if parent:
                    date_text = parent.get_text(strip=True)
                    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", date_text)
                    if date_match:
                        date_str = date_match.group(1)

                # 如果父元素没有日期，尝试从整个容器获取
                if not date_str and container:
                    date_text = container.get_text(strip=True)
                    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", date_text)
                    if date_match:
                        date_str = date_match.group(1)

                items.append({
                    "title": title,
                    "url": href,
                    "date": date_str,
                })

        # 如果还是没有结果，尝试更通用的方法
        if not items:
            all_links = soup.find_all("a", href=True)
            for link in all_links:
                title = link.get_text(strip=True)
                href = link.get("href", "")

                # 法规链接通常包含特定模式
                if not title or len(title) < 10:
                    continue

                # 跳过导航链接
                if any(x in href for x in ["/fl.html", "/search", "javascript", "#", "mailto"]):
                    continue

                # 查找包含日期的元素
                date_str = ""
                parent = link.parent
                if parent:
                    date_text = parent.get_text(strip=True)
                    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", date_text)
                    if date_match:
                        date_str = date_match.group(1)

                items.append({
                    "title": title,
                    "url": href,
                    "date": date_str,
                })

        return items

    def _item_to_law_from_web(self, item: dict) -> Optional[Law]:
        """Convert a web search result item to a Law dataclass."""
        title = item.get("title", "").strip()
        if not title:
            return None

        detail_url = item.get("url", "") or ""
        if detail_url and not detail_url.startswith("http"):
            detail_url = urljoin(self.DETAIL_BASE, detail_url)

        if not detail_url:
            law_hash = hashlib.md5(title.encode()).hexdigest()
        else:
            law_hash = hashlib.md5(detail_url.encode()).hexdigest()

        publish_date = item.get("date", "")

        # 获取全文
        raw_text = ""
        if detail_url:
            raw_text = self._fetch_full_text(detail_url) or title

        return Law(
            id=law_hash,
            title=title,
            source="npc",
            source_url=detail_url or "",
            publish_date=publish_date or None,
            content_hash=hashlib.md5(raw_text.encode()).hexdigest(),
            raw_text=raw_text,
        )

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

        # 使用 Playwright 获取页面
        html_content = asyncio.run(
            self.playwright.fetch_page(url, wait_for_selector=".content", timeout=30000)
        )

        if not html_content:
            return None

        try:
            soup = BeautifulSoup(html_content, "lxml")

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
