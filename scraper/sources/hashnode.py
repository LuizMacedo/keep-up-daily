"""Hashnode scraper — uses the public GraphQL API (best-effort)."""

import logging

import requests

from .base import Article, BaseScraper
from ..config import SOURCES, REQUEST_TIMEOUT, USER_AGENT

logger = logging.getLogger(__name__)

HASHNODE_GQL = "https://gql.hashnode.com"

# -----------------------------------------------------------------------
# GraphQL query – fetches the public best / trending feed.
# If Hashnode restricts this endpoint in the future, the scraper
# will fail gracefully and the other sources will still provide data.
# -----------------------------------------------------------------------
FEED_QUERY = """
query FetchFeed($first: Int!) {
  feed(first: $first, filter: { type: BEST }) {
    edges {
      node {
        title
        brief
        url
        author { username }
        readTimeInMinutes
        reactionCount
        responseCount
        publishedAt
        tags { name }
      }
    }
  }
}
"""


class HashnodeScraper(BaseScraper):
    name = "hashnode"
    base_url = HASHNODE_GQL

    def fetch(self) -> list[Article]:
        cfg = SOURCES.get("hashnode", {})
        if not cfg.get("enabled", True):
            return []

        limit = cfg.get("max_articles", 20)
        articles: list[Article] = []

        try:
            headers = {
                "User-Agent": USER_AGENT,
                "Content-Type": "application/json",
            }
            resp = requests.post(
                HASHNODE_GQL,
                json={"query": FEED_QUERY, "variables": {"first": limit}},
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()

            edges = (
                data.get("data", {}).get("feed", {}).get("edges", [])
            )

            for edge in edges:
                node = edge.get("node", {})
                tags = [
                    t.get("name", "")
                    for t in (node.get("tags") or [])
                    if t.get("name")
                ]
                author_obj = node.get("author") or {}

                a = Article(
                    title=node.get("title", ""),
                    url=node.get("url", ""),
                    source="hashnode",
                    description=(node.get("brief") or "")[:300],
                    author=author_obj.get("username", ""),
                    tags=tags,
                    score=node.get("reactionCount", 0),
                    comments_count=node.get("responseCount", 0),
                    reading_time_min=node.get("readTimeInMinutes", 0),
                    published_at=node.get("publishedAt", ""),
                )
                if a.title and a.url:
                    articles.append(a)

            logger.info("Hashnode: fetched %d articles", len(articles))
        except Exception as exc:
            logger.error("Hashnode scraper error: %s", exc)

        return articles
