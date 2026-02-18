"""Base scraper interface and common Article data model."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass
class Article:
    """Normalised representation of a single piece of content."""

    title: str
    url: str
    source: str
    description: str = ""
    author: str = ""
    tags: list[str] = field(default_factory=list)
    category: str = "general"
    score: int = 0
    comments_count: int = 0
    reading_time_min: int = 0
    published_at: str = ""
    fetched_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    language: str = "en"

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "Article":
        known = {k for k in Article.__dataclass_fields__}
        return Article(**{k: v for k, v in data.items() if k in known})


class BaseScraper:
    """Abstract base class every source scraper must extend."""

    name: str = "base"
    base_url: str = ""

    def fetch(self) -> list[Article]:
        """Return a list of Articles from the source.

        Subclasses **must** override this method.
        """
        raise NotImplementedError(f"{self.name} scraper must implement fetch()")

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} source='{self.name}'>"
