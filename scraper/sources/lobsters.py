"""Lobste.rs scraper — uses the public JSON API."""

import logging

import requests

from .base import Article, BaseScraper
from ..config import SOURCES, REQUEST_TIMEOUT, USER_AGENT

logger = logging.getLogger(__name__)


class LobstersScraper(BaseScraper):
    name = "lobsters"
    base_url = "https://lobste.rs"

    def fetch(self) -> list[Article]:
        cfg = SOURCES.get("lobsters", {})
        if not cfg.get("enabled", True):
            return []

        limit = cfg.get("max_articles", 25)
        articles: list[Article] = []
        headers = {"User-Agent": USER_AGENT}

        try:
            resp = requests.get(
                f"{self.base_url}/hottest.json",
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()

            for item in resp.json()[:limit]:
                url = item.get("url") or item.get("comments_url", "")

                submitter = item.get("submitter_user")
                author = ""
                if isinstance(submitter, dict):
                    author = submitter.get("username", "")
                elif isinstance(submitter, str):
                    author = submitter

                a = Article(
                    title=item.get("title", ""),
                    url=url,
                    source="lobsters",
                    description=item.get("description", ""),
                    author=author,
                    tags=item.get("tags", []),
                    score=item.get("score", 0),
                    comments_count=item.get("comment_count", 0),
                )
                if a.title and a.url:
                    articles.append(a)

            logger.info("Lobsters: fetched %d articles", len(articles))
        except Exception as exc:
            logger.error("Lobsters scraper error: %s", exc)

        return articles
