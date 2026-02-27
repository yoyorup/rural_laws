"""Generic LawProcessor: uses a pluggable AI provider to parse and explain laws."""

import json
import logging
import re
from typing import Optional, Tuple, List

from config import CLAUDE_SYSTEM_PROMPT
from database.models import Law, Clause, LawSummary
from processors.ai_providers.base import BaseAIProvider
from processors.text_cleaner import extract_articles, truncate_for_api

logger = logging.getLogger(__name__)

# Reuse the same system prompt for all providers
_SYSTEM_PROMPT = CLAUDE_SYSTEM_PROMPT


class LawProcessor:
    """
    Uses a pluggable AI provider to:
    1. Parse a law's articles
    2. Generate plain-language explanations
    3. Generate real-world examples
    4. Generate a one-paragraph law summary
    """

    def __init__(self, provider: BaseAIProvider):
        self.provider = provider

    def process_law(self, law: Law) -> Tuple[List[Clause], Optional[LawSummary]]:
        """Process a single law through the AI provider.

        Returns:
            (clauses, summary) - list of Clause objects and an optional LawSummary
        """
        if not law.raw_text or len(law.raw_text.strip()) < 50:
            logger.warning(
                f"Law '{law.title}' has insufficient text, skipping AI processing"
            )
            return [], None

        text = truncate_for_api(law.raw_text, max_chars=8000)
        user_prompt = self._build_prompt(law.title, text)

        logger.info(f"Processing law with {self.provider.name}: {law.title}")
        raw_response = self.provider.complete(_SYSTEM_PROMPT, user_prompt)

        if not raw_response:
            logger.error(
                f"Provider '{self.provider.name}' returned empty response for law: {law.title}"
            )
            return [], None

        return self._parse_response(law.id, raw_response, law.raw_text)

    def _build_prompt(self, title: str, text: str) -> str:
        return (
            f"法律名称：{title}\n\n"
            f"法律全文：\n{text}\n\n"
            "请按照系统提示中的 JSON 格式，解读上述法律条文。"
        )

    def _parse_response(
        self, law_id: str, response_text: str, original_text: str
    ) -> Tuple[List[Clause], Optional[LawSummary]]:
        """Parse the AI JSON response into Clause and LawSummary objects."""
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("AI response is not valid JSON, attempting extraction")
            data = self._extract_json_from_text(text)
            if data is None:
                return self._fallback_parse(law_id, original_text), None

        clauses = []
        for item in data.get("clauses", []):
            clause = Clause(
                law_id=law_id,
                article_no=item.get("article_no", "").strip(),
                raw_text=item.get("raw_text", "").strip(),
                explanation=item.get("explanation", "").strip(),
                example=item.get("example", "").strip(),
            )
            if clause.article_no or clause.raw_text:
                clauses.append(clause)

        summary_text = data.get("summary", "").strip()
        summary = LawSummary(law_id=law_id, summary=summary_text) if summary_text else None

        logger.info(f"Parsed {len(clauses)} clauses for law_id={law_id}")
        return clauses, summary

    def _extract_json_from_text(self, text: str) -> Optional[dict]:
        """Try to find a JSON object in text that may have surrounding noise."""
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return None

    def _fallback_parse(self, law_id: str, text: str) -> List[Clause]:
        """Create basic Clause objects from article extraction without explanations."""
        articles = extract_articles(text)
        clauses = []
        for art in articles:
            clauses.append(Clause(
                law_id=law_id,
                article_no=art["article_no"],
                raw_text=art["text"],
                explanation="（解读暂不可用）",
                example="",
            ))
        return clauses
