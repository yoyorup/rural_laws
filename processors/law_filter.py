"""Rural keyword filtering and relevance scoring for laws."""

import re
from typing import List

from config import RURAL_KEYWORDS
from database.models import Law

# Weight categories: higher = more rural-relevant
HIGH_WEIGHT_KEYWORDS = {
    "农村": 3.0, "农民": 3.0, "乡村振兴": 3.0, "农业农村": 3.0,
    "土地承包": 2.5, "宅基地": 2.5, "乡村": 2.0, "农用地": 2.0,
}

MEDIUM_WEIGHT_KEYWORDS = {
    "土地": 1.5, "农业": 1.5, "耕地": 1.5, "承包": 1.5,
    "集体经济": 1.5, "合作社": 1.5, "家庭农场": 1.5,
}

LOW_WEIGHT_KEYWORDS = {
    "粮食": 1.0, "种植": 1.0, "养殖": 1.0, "林地": 1.0,
    "渔业": 1.0, "牧业": 1.0, "乡镇": 1.0, "村委": 1.0,
    "振兴": 1.0, "扶贫": 1.0, "惠农": 1.0,
}

ALL_WEIGHTS = {**HIGH_WEIGHT_KEYWORDS, **MEDIUM_WEIGHT_KEYWORDS, **LOW_WEIGHT_KEYWORDS}

MIN_RELEVANCE_SCORE = 0.5  # minimum score to keep a law


def calculate_relevance_score(title: str, text: str = "") -> float:
    """
    Calculate a relevance score based on keyword frequency and weight.
    Score = sum of (weight * sqrt(count)) for each keyword found.
    Normalized to [0, 10].
    """
    import math

    combined = title * 3 + " " + text  # title gets 3x weight
    score = 0.0

    for keyword, weight in ALL_WEIGHTS.items():
        count = combined.count(keyword)
        if count > 0:
            score += weight * math.sqrt(count)

    # Normalize: cap at 10
    return min(round(score, 2), 10.0)


def is_rural_relevant(title: str, text: str = "") -> bool:
    """Quick check: does this law contain any rural keywords?"""
    combined = title + " " + text[:500]  # check first 500 chars of text
    return any(kw in combined for kw in RURAL_KEYWORDS)


def filter_laws(laws: List[Law]) -> List[Law]:
    """
    Filter and score a list of laws for rural relevance.
    Updates each law's relevance_score and is_rural flag.
    Returns only laws with relevance_score >= MIN_RELEVANCE_SCORE.
    """
    result = []
    for law in laws:
        score = calculate_relevance_score(law.title, law.raw_text)
        law.relevance_score = score
        if score >= MIN_RELEVANCE_SCORE:
            law.is_rural = 1
            result.append(law)
        else:
            law.is_rural = 0

    # Sort by score descending
    result.sort(key=lambda x: x.relevance_score, reverse=True)
    return result
