"""MD5-based deduplication for laws (new vs. updated vs. unchanged)."""

import hashlib
import logging
from enum import Enum
from typing import List, Tuple

from database.models import Law
from database import db_manager

logger = logging.getLogger(__name__)


class LawStatus(Enum):
    NEW = "new"
    UPDATED = "updated"
    UNCHANGED = "unchanged"


def compute_content_hash(text: str) -> str:
    """Compute MD5 hash of law text content."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def classify_laws(laws: List[Law]) -> List[Tuple[Law, LawStatus]]:
    """
    For each law, determine whether it's new, updated, or unchanged
    by comparing the content_hash against what's stored in the database.
    Also updates the law's content_hash if not set.
    """
    results = []

    for law in laws:
        # Ensure content_hash is set
        if not law.content_hash:
            law.content_hash = compute_content_hash(law.raw_text)

        existing = db_manager.get_law(law.id)

        if existing is None:
            status = LawStatus.NEW
        elif existing.content_hash != law.content_hash:
            status = LawStatus.UPDATED
        else:
            status = LawStatus.UNCHANGED

        results.append((law, status))

    return results


def deduplicate_within_batch(laws: List[Law]) -> List[Law]:
    """Remove duplicate laws within a single batch (same id = same URL hash)."""
    seen = {}
    for law in laws:
        if law.id not in seen:
            # Prefer laws with more content
            seen[law.id] = law
        elif len(law.raw_text) > len(seen[law.id].raw_text):
            seen[law.id] = law
    return list(seen.values())
