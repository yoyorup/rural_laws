"""Data models (dataclasses) for the Rural Law Daily Review System."""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class Law:
    id: str                          # MD5 hash of source_url
    title: str
    source: str                      # npc / moa / gov
    source_url: str
    raw_text: str = ""
    publish_date: Optional[str] = None
    effective_date: Optional[str] = None
    content_hash: Optional[str] = None
    fetched_at: Optional[str] = None
    is_rural: int = 1
    relevance_score: float = 0.0

    def __post_init__(self):
        if self.fetched_at is None:
            self.fetched_at = datetime.now().isoformat()


@dataclass
class Clause:
    law_id: str
    article_no: str                  # 第X条
    raw_text: str
    explanation: str = ""
    example: str = ""
    id: Optional[int] = None
    created_at: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


@dataclass
class LawSummary:
    law_id: str
    summary: str
    created_at: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


@dataclass
class NewsItem:
    law_id: str
    title: str
    url: str
    source: str
    published_at: Optional[str] = None
    snippet: str = ""
    id: Optional[int] = None


@dataclass
class RunLog:
    run_date: str
    laws_fetched: int = 0
    laws_new: int = 0
    laws_updated: int = 0
    status: str = "running"
    error_msg: Optional[str] = None
    id: Optional[int] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None

    def __post_init__(self):
        if self.started_at is None:
            self.started_at = datetime.now().isoformat()


@dataclass
class LawWithDetails:
    """Aggregated view of a law with its clauses, summary, and news."""
    law: Law
    clauses: List[Clause] = field(default_factory=list)
    summary: Optional[LawSummary] = None
    news: List[NewsItem] = field(default_factory=list)
