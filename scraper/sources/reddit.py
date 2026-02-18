"""Reddit scraper — uses the public JSON endpoints."""

import logging
import time

import requests

from .base import Article, BaseScraper
from ..config import SOURCES, REQUEST_TIMEOUT, USER_AGENT, REQUEST_DELAY

logger = logging.getLogger(__name__)


class RedditScraper(BaseScraper):
    name = "reddit"
    base_url = "https://www.reddit.com"

    def fetch(self) -> list[Article]:
        cfg = SOURCES.get("reddit", {})
        if not cfg.get("enabled", True):
            return []

        subreddits: list[str] = cfg.get("subreddits", ["programming"])
        max_per = cfg.get("max_per_subreddit", 10)
        articles: list[Article] = []
        seen: set[str] = set()
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}

        for sub in subreddits:
            try:
                resp = requests.get(
                    f"{self.base_url}/r/{sub}/hot.json",
                    params={"limit": max_per, "t": "day"},
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                )
                resp.raise_for_status()

                children = resp.json().get("data", {}).get("children", [])
                for post in children:
                    d = post.get("data", {})
                    if d.get("stickied"):
                        continue

                    url = d.get("url", "")
                    permalink = f"https://www.reddit.com{d.get('permalink', '')}"
                    target = url if url and not url.startswith("/r/") else permalink

                    if target in seen:
                        continue
                    seen.add(target)

                    selftext = d.get("selftext", "")
                    desc = (selftext[:300] + "...") if len(selftext) > 300 else selftext

                    a = Article(
                        title=d.get("title", ""),
                        url=target,
                        source="reddit",
                        description=desc,
                        author=d.get("author", ""),
                        tags=[f"r/{sub}"],
                        score=d.get("score", 0),
                        comments_count=d.get("num_comments", 0),
                    )
                    if a.title and a.url:
                        articles.append(a)

                time.sleep(REQUEST_DELAY)
            except Exception as exc:
                logger.error("Reddit r/%s error: %s", sub, exc)

        logger.info("Reddit: fetched %d posts", len(articles))
        return articles
