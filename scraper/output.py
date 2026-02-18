"""Data output – JSON persistence and retention management."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .sources.base import Article
from .config import DATA_DIR, RETENTION_DAYS

logger = logging.getLogger(__name__)


def save_daily_data(
    articles: list[Article],
    digest: list[dict] | None = None,
    date: str | None = None,
) -> Path:
    """Write today's digest + raw articles to ``data/<date>.json``."""
    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    filepath = DATA_DIR / f"{date}.json"

    payload = {
        "date": date,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "digest": digest or [],
        "digest_count": len(digest or []),
        "raw_article_count": len(articles),
        "sources": sorted(set(a.source for a in articles)),
        "articles": [a.to_dict() for a in articles],
    }

    filepath.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(
        "Saved %d digest entries + %d raw articles → %s",
        len(digest or []),
        len(articles),
        filepath,
    )
    return filepath


def update_index() -> Path:
    """Regenerate ``data/index.json`` with the list of available dates."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    dates = sorted(
        [f.stem for f in DATA_DIR.glob("*.json") if f.stem != "index"],
        reverse=True,
    )

    index = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "available_dates": dates,
        "total_days": len(dates),
    }

    index_path = DATA_DIR / "index.json"
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Index updated: %d dates available", len(dates))
    return index_path


def cleanup_old_data() -> int:
    """Delete data files older than *RETENTION_DAYS*. Returns count removed."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)).strftime(
        "%Y-%m-%d"
    )
    removed = 0
    for f in DATA_DIR.glob("*.json"):
        if f.stem != "index" and f.stem < cutoff:
            f.unlink()
            removed += 1
            logger.info("Removed old data: %s", f.name)
    return removed
