"""Chinese HTML text normalization and cleaning utilities."""

import re
from typing import Optional

from bs4 import BeautifulSoup


def clean_html_text(html: str) -> str:
    """
    Convert HTML to clean plain text:
    - Remove scripts, styles, nav, footer elements
    - Preserve article structure (newlines between paragraphs)
    - Normalize whitespace
    - Handle Chinese-specific encoding issues
    """
    if not html:
        return ""

    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        # Fallback: strip tags with regex
        return strip_tags_simple(html)

    # Remove noise elements
    for tag in soup.find_all(["script", "style", "nav", "footer", "header",
                               "aside", "noscript", "iframe"]):
        tag.decompose()

    # Get text with newlines between block elements
    lines = []
    for elem in soup.find_all(["p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6",
                                "article", "section", "blockquote", "td", "th"]):
        text = elem.get_text(separator=" ", strip=True)
        if text:
            lines.append(text)

    if not lines:
        text = soup.get_text(separator="\n", strip=True)
    else:
        text = "\n".join(lines)

    return normalize_whitespace(text)


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in Chinese text."""
    if not text:
        return ""

    # Replace multiple spaces/tabs with single space
    text = re.sub(r"[ \t]+", " ", text)

    # Replace 3+ consecutive newlines with 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove leading/trailing whitespace per line
    lines = [line.strip() for line in text.splitlines()]

    # Remove empty lines at start/end
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()

    return "\n".join(lines)


def strip_tags_simple(html: str) -> str:
    """Fallback: remove all HTML tags with regex."""
    text = re.sub(r"<[^>]+>", "", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&quot;", '"', text)
    return normalize_whitespace(text)


def extract_articles(text: str) -> list[dict]:
    """
    Parse law text into article segments.
    Returns list of {"article_no": "第X条", "text": "..."}
    """
    # Pattern: 第X条 (optional 　/space) content
    pattern = re.compile(
        r"(第[一二三四五六七八九十百千\d]+条)\s*[　\s]*(.*?)(?=第[一二三四五六七八九十百千\d]+条|\Z)",
        re.DOTALL,
    )

    articles = []
    for match in pattern.finditer(text):
        article_no = match.group(1).strip()
        content = normalize_whitespace(match.group(2))
        if content:
            articles.append({"article_no": article_no, "text": content})

    return articles


def truncate_for_api(text: str, max_chars: int = 8000) -> str:
    """Truncate text for API calls while keeping whole sentences."""
    if len(text) <= max_chars:
        return text

    # Find last sentence boundary before limit
    truncated = text[:max_chars]
    last_period = max(
        truncated.rfind("。"),
        truncated.rfind("！"),
        truncated.rfind("？"),
    )
    if last_period > max_chars * 0.5:
        return truncated[: last_period + 1]
    return truncated
