"""Source scrapers for keep-up-daily."""

from .devto import DevtoScraper
from .hackernews import HackerNewsScraper
from .github_trending import GitHubTrendingScraper
from .reddit import RedditScraper
from .lobsters import LobstersScraper
from .hashnode import HashnodeScraper

ALL_SCRAPERS = [
    DevtoScraper,
    HackerNewsScraper,
    GitHubTrendingScraper,
    RedditScraper,
    LobstersScraper,
    HashnodeScraper,
]

__all__ = [
    "DevtoScraper",
    "HackerNewsScraper",
    "GitHubTrendingScraper",
    "RedditScraper",
    "LobstersScraper",
    "HashnodeScraper",
    "ALL_SCRAPERS",
]
