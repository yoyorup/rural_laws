"""Fetcher for 农业农村部 (moa.gov.cn) policy documents."""

import hashlib
import logging
import re
from datetime import datetime, timedelta
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from config import MOA_BASE_URL, MOA_POLICY_URL, NPC_DAYS_BACK
from database.models import Law
from fetchers.base_fetcher import BaseFetcher
from processors.text_cleaner import clean_html_text

logger = logging.getLogger(__name__)


class MoaFetcher(BaseFetcher):
    """
    Fetches policy documents and regulations from the
    Ministry of Agriculture and Rural Affairs (moa.gov.cn).
    """

    POLICY_SECTIONS = [
        "https://www.moa.gov.cn/gk/zcfg/",           # 法规
        "https://www.moa.gov.cn/gk/zcfg/nybgz/",     # 农业部规章
        "https://www.moa.gov.cn/gk/zcfg/flfg/",      # 法律法规
    ]

    def fetch_recent_laws(self, days_back: int = NPC_DAYS_BACK) -> List[Law]:
        """Fetch recent policy documents from MOA."""
        laws = []
        cutoff = datetime.now() - timedelta(days=days_back)

        for section_url in self.POLICY_SECTIONS:
            self.logger.info(f"Fetching MOA section: {section_url}")
            section_laws = self._fetch_section(section_url, cutoff)
            laws.extend(section_laws)
            self.polite_sleep(1.5)

        # Deduplicate
        seen = {}
        for law in laws:
            if law.id not in seen:
                seen[law.id] = law
        return list(seen.values())

    def _fetch_section(self, section_url: str, cutoff: datetime) -> List[Law]:
        """Fetch a listing page and extract law links."""
        resp = self.get(section_url)
        if resp is None:
            return []

        try:
            resp.encoding = resp.apparent_encoding or "utf-8"
            soup = BeautifulSoup(resp.text, "lxml")
        except Exception as e:
            self.logger.error(f"Error parsing {section_url}: {e}")
            return []

        laws = []
        # Find list items with dates
        list_items = soup.select("ul.list li, .newslist li, .policy-list li, li")

        for item in list_items:
            link = item.find("a", href=True)
            if not link:
                continue

            title = link.get_text(strip=True)
            href = link["href"]
            if not href.startswith("http"):
                href = urljoin(section_url, href)

            # Extract date from item text
            date_str = self._extract_date_from_text(item.get_text())
            if date_str:
                try:
                    item_date = datetime.strptime(date_str, "%Y-%m-%d")
                    if item_date < cutoff:
                        continue
                except ValueError:
                    pass

            if not title or len(title) < 4:
                continue

            law = self._fetch_law_detail(title, href, date_str)
            if law:
                laws.append(law)
                self.polite_sleep(0.8)

        return laws

    def _extract_date_from_text(self, text: str) -> Optional[str]:
        """Extract YYYY-MM-DD from arbitrary text."""
        patterns = [
            r"(\d{4}-\d{2}-\d{2})",
            r"(\d{4})年(\d{1,2})月(\d{1,2})日",
            r"(\d{4})\.(\d{2})\.(\d{2})",
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                if len(m.groups()) == 1:
                    return m.group(1)
                elif len(m.groups()) == 3:
                    y, mo, d = m.groups()
                    return f"{y}-{int(mo):02d}-{int(d):02d}"
        return None

    def _fetch_law_detail(
        self, title: str, url: str, date_str: Optional[str]
    ) -> Optional[Law]:
        """Fetch detail page and construct Law object."""
        resp = self.get(url)
        if resp is None:
            return None

        try:
            resp.encoding = resp.apparent_encoding or "utf-8"
            soup = BeautifulSoup(resp.text, "lxml")

            # Extract content
            content_elem = (
                soup.select_one(".article-content")
                or soup.select_one("#content")
                or soup.select_one(".TRS_Editor")
                or soup.select_one("article")
                or soup.find("div", class_=re.compile(r"content|article|main"))
            )
            raw_text = clean_html_text(str(content_elem)) if content_elem else title

            law_hash = hashlib.md5(url.encode()).hexdigest()
            return Law(
                id=law_hash,
                title=title,
                source="moa",
                source_url=url,
                publish_date=date_str,
                content_hash=hashlib.md5(raw_text.encode()).hexdigest(),
                raw_text=raw_text,
            )
        except Exception as e:
            self.logger.error(f"Error fetching MOA detail {url}: {e}")
            return None
