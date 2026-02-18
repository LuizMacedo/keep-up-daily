"""Main orchestrator – runs all scrapers, categorises, and outputs data."""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone

from .sources import ALL_SCRAPERS
from .sources.base import Article
from .categorizer import categorize_articles
from .curator import create_digest
from .output import save_daily_data, update_index, cleanup_old_data

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _deduplicate(articles: list[Article]) -> list[Article]:
    seen: set[str] = set()
    unique: list[Article] = []
    for a in articles:
        key = a.url.rstrip("/").lower()
        if key not in seen:
            seen.add(key)
            unique.append(a)
    return unique


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------
def run() -> None:
    logger.info("=" * 60)
    logger.info("Keep Up Daily — starting scraper run")
    logger.info("=" * 60)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    all_articles: list[Article] = []
    stats: dict[str, int] = {}

    for scraper_cls in ALL_SCRAPERS:
        scraper = scraper_cls()
        logger.info("Running %s …", scraper.name)
        try:
            arts = scraper.fetch()
            stats[scraper.name] = len(arts)
            all_articles.extend(arts)
            logger.info("  → %d items", len(arts))
        except Exception as exc:
            logger.error("  ✗ %s failed: %s", scraper.name, exc)
            stats[scraper.name] = 0

    before = len(all_articles)
    all_articles = _deduplicate(all_articles)
    logger.info("Dedup: %d → %d articles", before, len(all_articles))

    all_articles = categorize_articles(all_articles)
    all_articles.sort(key=lambda a: a.score, reverse=True)

    # ── AI digest: distil all articles into ~12 readable entries ──
    digest = create_digest(all_articles)

    save_daily_data(all_articles, digest=digest, date=today)
    update_index()

    removed = cleanup_old_data()
    if removed:
        logger.info("Cleaned up %d old data file(s)", removed)

    logger.info("=" * 60)
    logger.info(
        "Done: %d articles from %d sources",
        len(all_articles),
        sum(1 for v in stats.values() if v > 0),
    )
    for src, cnt in sorted(stats.items()):
        logger.info("  %s: %d", src, cnt)
    logger.info("=" * 60)


if __name__ == "__main__":
    run()
