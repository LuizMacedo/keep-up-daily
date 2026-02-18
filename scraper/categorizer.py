"""Keyword-based article categoriser."""

from __future__ import annotations

import logging
import re

from .sources.base import Article
from .config import CATEGORIES, DEFAULT_CATEGORY

logger = logging.getLogger(__name__)


def _build_text(article: Article) -> str:
    """Combine article fields into a single lowercase searchable string."""
    return " ".join(
        [
            article.title,
            article.description,
            " ".join(article.tags),
        ]
    ).lower()


def categorize_article(article: Article) -> str:
    """Return the best-matching category key for *article*."""
    text = _build_text(article)

    best_cat = DEFAULT_CATEGORY
    best_score = 0

    for cat, info in CATEGORIES.items():
        score = 0
        for kw in info["keywords"]:
            # Short keywords (<= 3 chars) need word-boundary matching
            if len(kw) <= 3:
                if re.search(rf"\b{re.escape(kw)}\b", text, re.IGNORECASE):
                    score += 2
            else:
                if kw.lower() in text:
                    score += 1

        if score > best_score:
            best_score = score
            best_cat = cat

    return best_cat


def categorize_articles(articles: list[Article]) -> list[Article]:
    """Categorise every article in-place and return the list."""
    for a in articles:
        a.category = categorize_article(a)

    dist: dict[str, int] = {}
    for a in articles:
        dist[a.category] = dist.get(a.category, 0) + 1
    logger.info("Category distribution: %s", dist)

    return articles
