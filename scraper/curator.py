"""AI-powered daily digest creator using GitHub Models API.

Reads ALL scraped articles and produces ~12 original digest entries:
the AI writes new titles and bodies explaining what developers need
to know, in both English and Brazilian Portuguese.

Falls back to a score-based summary when GITHUB_TOKEN is unavailable.
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections import defaultdict

import requests

from .sources.base import Article
from .config import AI_CONFIG, CATEGORIES

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────
ENDPOINT = AI_CONFIG["endpoint"]
MODEL = AI_CONFIG["model"]
TEMPERATURE = AI_CONFIG["temperature"]
TARGET_ENTRIES = AI_CONFIG["target_entries"]
TIMEOUT = AI_CONFIG["request_timeout"]

CATEGORY_EMOJI = {
    "ai": "🤖",
    "web": "🌐",
    "devops": "☁️",
    "languages": "💻",
    "frameworks": "🧩",
    "security": "🔒",
    "career": "🚀",
    "general": "📌",
}


# ──────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────
def create_digest(articles: list[Article]) -> list[dict]:
    """Create daily digest entries from all scraped articles.

    Returns a list of dicts, each with:
        title_en, title_pt, body_en, body_pt, category, emoji, sources
    """
    token = os.environ.get("GITHUB_TOKEN", "").strip()

    if not token or not AI_CONFIG["enabled"]:
        logger.warning(
            "AI digest disabled or no GITHUB_TOKEN – using fallback digest"
        )
        return _fallback_digest(articles)

    condensed = _condense_articles(articles)
    digest = _call_ai(condensed, articles, token)

    if not digest:
        logger.warning("AI returned nothing – falling back to score-based digest")
        return _fallback_digest(articles)

    logger.info(
        "AI digest complete: %d entries from %d articles", len(digest), len(articles)
    )
    return digest


# ──────────────────────────────────────────────────
# AI call
# ──────────────────────────────────────────────────
def _condense_articles(articles: list[Article]) -> list[dict]:
    """Compact representation of articles for the AI prompt."""
    return [
        {
            "id": idx,
            "title": a.title,
            "source": a.source,
            "category": a.category,
            "desc": (a.description or "")[:200],
            "score": a.score,
            "tags": a.tags[:4],
        }
        for idx, a in enumerate(articles)
    ]


def _call_ai(
    condensed: list[dict], articles: list[Article], token: str
) -> list[dict]:
    """Send all articles to GitHub Models and get back digest entries."""
    cat_counts: dict[str, int] = defaultdict(int)
    for a in articles:
        cat_counts[a.category] += 1
    cat_summary = ", ".join(f"{c}: {n}" for c, n in sorted(cat_counts.items()))

    prompt = f"""You have {len(condensed)} tech articles scraped today from Dev.to, \
Hacker News, GitHub Trending, Reddit, and Lobsters.

Category breakdown: {cat_summary}

**Your mission:** Create a daily developer digest with exactly {TARGET_ENTRIES} entries.

Each entry is an ORIGINAL piece written by you. You are NOT linking or summarising \
a single article — you are DIGESTING multiple related articles into one engaging story \
that tells the reader what they need to know. Merge related articles when they cover \
the same topic.

For EACH entry provide:
1. **title_en / title_pt** – catchy, informative headline (English & Brazilian Portuguese)
2. **body_en / body_pt** – 2-3 short paragraphs:
   • Paragraph 1: What happened or what is this about (hook the reader)
   • Paragraph 2: Why it matters to developers – real-world impact
   • Paragraph 3 (optional): Key takeaway, what to try, or what to watch for next
3. **category** – one of: ai, web, devops, languages, frameworks, security, career, general
4. **source_ids** – array of article IDs (from the "id" field) that informed the entry

Writing rules:
- Conversational and lively, like a smart friend explaining the news over coffee
- Use specific details, numbers, project names, and version numbers from the articles
- Vary sentence length — mix short punchy sentences with longer explanatory ones
- Each body_en and body_pt should be 80-150 words (short enough to enjoy, long enough to learn)
- Make it the kind of read someone looks forward to every morning
- Cover DIVERSE categories — spread across AI, web, devops, languages, etc.
- Separate paragraphs with a blank line

Articles:
{json.dumps(condensed, ensure_ascii=False)}

Respond with ONLY a JSON array (no fences, no commentary):
[{{"title_en":"...","title_pt":"...","body_en":"...","body_pt":"...","category":"...","source_ids":[0,3,7]}}]"""

    try:
        resp = requests.post(
            ENDPOINT,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a senior tech journalist writing a daily developer "
                            "newsletter. You digest raw scraped articles into original, "
                            "engaging stories developers will love reading every morning. "
                            "Respond ONLY with valid JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": TEMPERATURE,
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()

        raw = resp.json()["choices"][0]["message"]["content"]
        entries = _parse_json(raw)
        return _enrich_entries(entries, articles)

    except requests.exceptions.HTTPError as exc:
        code = exc.response.status_code if exc.response is not None else "?"
        logger.error("AI HTTP %s: %s", code, exc)
    except Exception as exc:
        logger.error("AI digest failed: %s", exc)

    return []


def _enrich_entries(
    raw_entries: list[dict], articles: list[Article]
) -> list[dict]:
    """Add emoji and resolve source_ids → source dicts."""
    digest: list[dict] = []
    for entry in raw_entries:
        cat = entry.get("category", "general")
        sources: list[dict] = []
        for sid in entry.get("source_ids", []):
            if isinstance(sid, int) and 0 <= sid < len(articles):
                a = articles[sid]
                sources.append(
                    {"title": a.title, "url": a.url, "source": a.source}
                )
        digest.append(
            {
                "title_en": entry.get("title_en", ""),
                "title_pt": entry.get("title_pt", ""),
                "body_en": entry.get("body_en", ""),
                "body_pt": entry.get("body_pt", ""),
                "category": cat,
                "emoji": CATEGORY_EMOJI.get(cat, "📌"),
                "sources": sources,
            }
        )
    return digest


def _parse_json(text: str) -> list[dict]:
    """Extract JSON array from model output, tolerating markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    return json.loads(text)


# ──────────────────────────────────────────────────
# Fallback (no AI available)
# ──────────────────────────────────────────────────
_CAT_LABELS = {
    "ai": ("AI & Machine Learning", "IA & Machine Learning"),
    "web": ("Web Development", "Desenvolvimento Web"),
    "devops": ("DevOps & Cloud", "DevOps & Nuvem"),
    "languages": ("Programming Languages", "Linguagens de Programação"),
    "frameworks": ("Frameworks & Tools", "Frameworks & Ferramentas"),
    "security": ("Security", "Segurança"),
    "career": ("Career & Community", "Carreira & Comunidade"),
    "general": ("General Tech", "Tecnologia em Geral"),
}

_CAT_ORDER = ("ai", "web", "devops", "languages", "frameworks", "security", "career", "general")


def _fallback_digest(articles: list[Article]) -> list[dict]:
    """Build a readable digest without AI by grouping top articles."""
    by_cat: dict[str, list[Article]] = defaultdict(list)
    for a in articles:
        by_cat[a.category].append(a)

    digest: list[dict] = []

    for cat in _CAT_ORDER:
        cat_articles = by_cat.get(cat, [])
        if not cat_articles:
            continue
        cat_articles.sort(key=lambda a: a.score, reverse=True)
        top = cat_articles[:3]
        en_label, pt_label = _CAT_LABELS.get(cat, (cat.title(), cat.title()))

        # Build readable body with article highlights
        items_en = []
        items_pt = []
        for a in top:
            desc = (a.description or "")[:250]
            line = f"**{a.title}** — {desc}" if desc else f"**{a.title}**"
            items_en.append(line)
            items_pt.append(line)

        body_en = (
            f"Here are today's most talked-about stories in {en_label.lower()}:\n\n"
            + "\n\n".join(items_en)
        )
        body_pt = (
            f"Veja os destaques de hoje em {pt_label.lower()}:\n\n"
            + "\n\n".join(items_pt)
        )

        sources = [
            {"title": a.title, "url": a.url, "source": a.source} for a in top
        ]

        digest.append(
            {
                "title_en": f"Today in {en_label}",
                "title_pt": f"Hoje em {pt_label}",
                "body_en": body_en,
                "body_pt": body_pt,
                "category": cat,
                "emoji": CATEGORY_EMOJI.get(cat, "📌"),
                "sources": sources,
            }
        )

    logger.info(
        "Fallback digest: %d entries from %d articles", len(digest), len(articles)
    )
    return digest
