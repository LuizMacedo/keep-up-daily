"""Dev.to scraper — uses the public REST API."""

import logging

import requests

from .base import Article, BaseScraper
from ..config import SOURCES, REQUEST_TIMEOUT, USER_AGENT

logger = logging.getLogger(__name__)


class DevtoScraper(BaseScraper):
    name = "devto"
    base_url = "https://dev.to/api"

    def fetch(self) -> list[Article]:
        cfg = SOURCES.get("devto", {})
        if not cfg.get("enabled", True):
            return []

        limit = cfg.get("max_articles", 30)
        articles: list[Article] = []

        try:
            headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
            resp = requests.get(
                f"{self.base_url}/articles",
                params={"top": 1, "per_page": limit},
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()

            for item in resp.json()[:limit]:
                a = Article(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    source="devto",
                    description=item.get("description", ""),
                    author=item.get("user", {}).get("username", ""),
                    tags=[t for t in item.get("tag_list", []) if t],
                    score=item.get("public_reactions_count", 0),
                    comments_count=item.get("comments_count", 0),
                    reading_time_min=item.get("reading_time_minutes", 0),
                    published_at=item.get("published_at", ""),
                )
                if a.title and a.url:
                    articles.append(a)

            logger.info("Dev.to: fetched %d articles", len(articles))
        except Exception as exc:
            logger.error("Dev.to scraper error: %s", exc)

        return articles
