"""HackerNews scraper — uses the official Firebase API."""

import logging
import time

import requests

from .base import Article, BaseScraper
from ..config import SOURCES, REQUEST_TIMEOUT, USER_AGENT

logger = logging.getLogger(__name__)

HN_API = "https://hacker-news.firebaseio.com/v0"


class HackerNewsScraper(BaseScraper):
    name = "hackernews"
    base_url = HN_API

    def fetch(self) -> list[Article]:
        cfg = SOURCES.get("hackernews", {})
        if not cfg.get("enabled", True):
            return []

        limit = cfg.get("max_articles", 30)
        articles: list[Article] = []
        headers = {"User-Agent": USER_AGENT}

        try:
            resp = requests.get(
                f"{HN_API}/topstories.json",
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            story_ids = resp.json()[:limit]

            for sid in story_ids:
                try:
                    r = requests.get(
                        f"{HN_API}/item/{sid}.json",
                        headers=headers,
                        timeout=REQUEST_TIMEOUT,
                    )
                    r.raise_for_status()
                    item = r.json()
                    if not item or item.get("type") != "story":
                        continue

                    url = item.get(
                        "url",
                        f"https://news.ycombinator.com/item?id={sid}",
                    )

                    a = Article(
                        title=item.get("title", ""),
                        url=url,
                        source="hackernews",
                        description="",
                        author=item.get("by", ""),
                        score=item.get("score", 0),
                        comments_count=item.get("descendants", 0),
                    )
                    if a.title:
                        articles.append(a)

                    time.sleep(0.05)  # be respectful
                except Exception as exc:
                    logger.warning("HN: story %s failed: %s", sid, exc)

            logger.info("HackerNews: fetched %d articles", len(articles))
        except Exception as exc:
            logger.error("HackerNews scraper error: %s", exc)

        return articles
