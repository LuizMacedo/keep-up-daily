"""GitHub Trending scraper — scrapes the trending page."""

import logging

import requests
from bs4 import BeautifulSoup

from .base import Article, BaseScraper
from ..config import SOURCES, REQUEST_TIMEOUT, USER_AGENT

logger = logging.getLogger(__name__)


class GitHubTrendingScraper(BaseScraper):
    name = "github_trending"
    base_url = "https://github.com/trending"

    def fetch(self) -> list[Article]:
        cfg = SOURCES.get("github_trending", {})
        if not cfg.get("enabled", True):
            return []

        languages: list[str] = cfg.get("languages", [""])
        articles: list[Article] = []
        seen: set[str] = set()
        headers = {"User-Agent": USER_AGENT}

        for lang in languages:
            try:
                url = f"{self.base_url}/{lang}" if lang else self.base_url
                resp = requests.get(
                    url,
                    params={"since": "daily"},
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                )
                resp.raise_for_status()

                soup = BeautifulSoup(resp.text, "lxml")
                for repo in soup.select("article.Box-row"):
                    try:
                        h2 = repo.select_one("h2 a")
                        if not h2:
                            continue
                        path = h2.get("href", "").strip()
                        repo_url = f"https://github.com{path}"
                        if repo_url in seen:
                            continue
                        seen.add(repo_url)

                        repo_name = path.strip("/")

                        desc_el = repo.select_one("p")
                        description = desc_el.get_text(strip=True) if desc_el else ""

                        lang_el = repo.select_one(
                            "[itemprop='programmingLanguage']"
                        )
                        prog_lang = lang_el.get_text(strip=True) if lang_el else ""

                        stars_today = 0
                        stars_el = repo.select_one(
                            "span.d-inline-block.float-sm-right"
                        )
                        if stars_el:
                            digits = "".join(
                                filter(str.isdigit, stars_el.get_text(strip=True))
                            )
                            stars_today = int(digits) if digits else 0

                        tags = [prog_lang.lower()] if prog_lang else []
                        articles.append(
                            Article(
                                title=repo_name,
                                url=repo_url,
                                source="github_trending",
                                description=description,
                                tags=tags,
                                score=stars_today,
                            )
                        )
                    except Exception as exc:
                        logger.warning("GitHub Trending: parse error: %s", exc)

            except Exception as exc:
                logger.error(
                    "GitHub Trending: failed for '%s': %s", lang or "all", exc
                )

        logger.info("GitHub Trending: fetched %d repos", len(articles))
        return articles
