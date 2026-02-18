"""AI-powered daily digest creator using GitHub Models API.

Reads ALL scraped articles and produces rich, self-contained digest entries:
the AI writes original mini-articles that teach the reader enough to skip the
original source if they choose — in both English and Brazilian Portuguese.

The number of entries is driven by content quality, not a hard cap.
Falls back to an expanded per-article digest when no AI token is available.
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
MAX_ENTRIES = AI_CONFIG["max_entries"]
FALLBACK_PER_CAT = AI_CONFIG["fallback_per_cat"]
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

# Token env var – prefer GH_MODELS_TOKEN (user PAT), fall back to GITHUB_TOKEN
_TOKEN_VARS = ("GH_MODELS_TOKEN", "GITHUB_TOKEN")


def _get_token() -> str:
    """Return the first non-empty token from known env vars."""
    for var in _TOKEN_VARS:
        val = os.environ.get(var, "").strip()
        if val:
            logger.info("Using token from $%s", var)
            return val
    return ""


# ──────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────
def create_digest(articles: list[Article]) -> list[dict]:
    """Create daily digest entries from all scraped articles.

    Returns a list of dicts, each with:
        title_en, title_pt, body_en, body_pt, category, emoji, sources
    """
    token = _get_token()

    if not token or not AI_CONFIG["enabled"]:
        logger.warning(
            "AI digest disabled or no token found in %s – using fallback digest",
            "/".join(_TOKEN_VARS),
        )
        return _fallback_digest(articles)

    condensed = _condense_articles(articles)
    digest = _call_ai(condensed, articles, token)

    if not digest:
        logger.warning("AI returned nothing – falling back")
        return _fallback_digest(articles)

    logger.info(
        "AI digest complete: %d entries from %d articles", len(digest), len(articles)
    )
    return digest


# ──────────────────────────────────────────────────
# AI call
# ──────────────────────────────────────────────────
def _condense_articles(articles: list[Article]) -> list[dict]:
    """Compact representation with richer descriptions for the AI."""
    return [
        {
            "id": idx,
            "title": a.title,
            "source": a.source,
            "category": a.category,
            "desc": (a.description or "")[:500],
            "score": a.score,
            "tags": a.tags[:6],
            "comments": a.comments_count,
            "author": a.author,
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

**Your mission:** Create a rich daily developer digest. You decide how many entries \
to write — produce one entry for every genuinely interesting or educational topic \
you find (typically 15–25, up to {MAX_ENTRIES}). Quality is paramount: a reader \
should be able to read ONLY your entry and feel they understand the topic without \
needing to click through to the original.

This is a **developer newsletter people look forward to every morning**. Each entry \
is a COMPLETE mini-article — after reading it, the developer should have learned \
something concrete they can use or discuss, not just be aware something exists.

## WHAT MAKES A GREAT ENTRY

Each entry must be SELF-CONTAINED and EDUCATIONAL. The reader should NOT need the \
original article. Think of it like a knowledgeable colleague summarizing an article \
for you at the coffee machine — but with real depth.

**Structure for each entry body (300-400 words per language):**

**Lead paragraph:** What is this about and why should a developer care RIGHT NOW? \
Open with impact — a concrete fact, a surprising number, or a real problem being solved.

**Technical deep-dive (1-2 paragraphs):** This is the core. Explain HOW it works:
- Architecture decisions, algorithms, data structures used
- Key APIs, function signatures, configuration patterns
- Performance characteristics: latency, throughput, memory, benchmarks
- Trade-offs and design choices — what did they optimize for and what did they sacrifice?
- Code snippets or pseudo-code when helpful (use \`inline code\` formatting)
- For projects: what language, what dependencies, what's the build/run story?
- For discussions: what's the core argument, what evidence supports it?

**Practical angle:** When would YOU use this? What real problem does it solve? \
How does it compare to existing tools? Is it production-ready or experimental? \
What are the gotchas?

**Takeaway:** One punchy line — the key insight the reader should remember.

## EXAMPLES OF GOOD vs BAD

BAD title: "AI Tools Are Trending"
GOOD title: "Alibaba's QwQ-32B Matches GPT-4o on Math Reasoning — At 1/10th the Cost"

BAD body: "A new AI tool was released that helps developers write code faster."
GOOD body: "**QwQ-32B** is a 32-billion parameter reasoning model from Alibaba that \
uses chain-of-thought prompting natively — no special system prompt needed. In the \
MATH-500 benchmark it scores 90.6%, just 1.2 points behind GPT-4o, while running \
on a single A100 GPU. The model uses a Mixture-of-Experts architecture with 8 active \
experts out of 64 total, which keeps inference cost at roughly $0.15/M input tokens \
via API..."

## WRITING RULES

- **Merge** related articles (e.g., 3 articles about the same GitHub repo → 1 entry)
- **Specific > vague** — "Uses HNSW indexing with 4-bit quantization" > "fast vector search"
- Include concrete details: library names, version numbers, API endpoints, benchmarks
- Use **bold** for key technical terms, project names, and numbers
- Use \`inline code\` for function names, CLI commands, config keys
- Bullet lists (- item) for features, comparisons, pros/cons
- Separate paragraphs with blank lines
- Be opinionated: "the clever part is…", "this matters because…"
- Vary sentence length — short punchy lines mixed with longer explanations
- Cover DIVERSE categories — at least 5 different categories across all entries
- Write both English and Brazilian Portuguese versions (not a translation — \
  adapt naturally to each language's style)

For EACH entry provide:
1. **title_en / title_pt** – specific headline hinting at the insight
2. **body_en / body_pt** – self-contained mini-article (300-400 words each)
3. **category** – one of: ai, web, devops, languages, frameworks, security, career, general
4. **source_ids** – array of article IDs that informed the entry

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
                            "You are a senior developer and tech journalist writing a "
                            "daily newsletter. Your readers are professional developers "
                            "who want to LEARN from each entry — they should finish "
                            "feeling they understand a topic deeply enough to discuss "
                            "it at work, without reading the original source. "
                            "Every entry is a self-contained mini-article with real "
                            "technical depth: architecture, APIs, benchmarks, trade-offs. "
                            "Write in both English and Brazilian Portuguese. "
                            "Respond ONLY with valid JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": TEMPERATURE,
                "max_tokens": 16000,
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()

        raw = resp.json()["choices"][0]["message"]["content"]
        logger.info("AI response length: %d chars", len(raw))
        entries = _parse_json(raw)
        logger.info("Parsed %d entries from AI", len(entries))
        return _enrich_entries(entries, articles)

    except requests.exceptions.HTTPError as exc:
        code = exc.response.status_code if exc.response is not None else "?"
        body = ""
        if exc.response is not None:
            try:
                body = exc.response.text[:500]
            except Exception:
                pass
        logger.error("AI HTTP %s: %s | body: %s", code, exc, body)
    except json.JSONDecodeError as exc:
        logger.error("AI returned invalid JSON: %s", exc)
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
    # Strip markdown code fences
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    # Sometimes models add trailing text after the array
    bracket_end = text.rfind("]")
    if bracket_end != -1:
        text = text[: bracket_end + 1]
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

_CAT_ORDER = (
    "ai", "web", "devops", "languages", "frameworks",
    "security", "career", "general",
)


def _fallback_digest(articles: list[Article]) -> list[dict]:
    """Build a richer per-article digest without AI.

    Picks the top FALLBACK_PER_CAT articles from each active category,
    producing a generous list so readers can browse and choose. Each entry
    includes all available metadata presented in a readable format.
    """
    by_cat: dict[str, list[Article]] = defaultdict(list)
    for a in articles:
        by_cat[a.category].append(a)

    # Sort each category by score descending
    for cat in by_cat:
        by_cat[cat].sort(key=lambda a: a.score, reverse=True)

    # Pick top N per category for diversity (no global hard cap)
    picks: list[Article] = []
    for cat in _CAT_ORDER:
        for a in by_cat.get(cat, [])[:FALLBACK_PER_CAT]:
            picks.append(a)

    digest: list[dict] = []
    for a in picks:
        cat = a.category
        en_label, pt_label = _CAT_LABELS.get(cat, (cat.title(), cat.title()))
        emoji = CATEGORY_EMOJI.get(cat, "📌")

        desc = (a.description or "").strip()
        title = a.title.strip()
        tags_str = ", ".join(f"`{t}`" for t in a.tags[:6]) if a.tags else ""
        score_str = f"{a.score:,}" if a.score else ""
        author_str = a.author or ""
        source_label = a.source.replace("_", " ").title()

        # ── Build a rich English body ──
        parts_en: list[str] = []

        if desc:
            parts_en.append(desc)
        else:
            parts_en.append(
                f"**{title}** caught attention in the {en_label.lower()} "
                f"space today."
            )

        # Technical context line
        context_parts: list[str] = []
        if tags_str:
            context_parts.append(f"Tags: {tags_str}")
        if author_str:
            context_parts.append(f"Author: **{author_str}**")
        if context_parts:
            parts_en.append(" · ".join(context_parts))

        # Community signals
        signal_parts: list[str] = []
        if score_str:
            signal_parts.append(f"**{score_str}** points")
        if a.comments_count:
            signal_parts.append(f"**{a.comments_count}** comments")
        signal_parts.append(f"via **{source_label}**")

        parts_en.append(
            "Community buzz: " + ", ".join(signal_parts) + ". "
            "Check the original source below for the full story."
        )

        body_en = "\n\n".join(parts_en)

        # ── Build a rich Portuguese body ──
        parts_pt: list[str] = []

        if desc:
            parts_pt.append(desc)
        else:
            parts_pt.append(
                f"**{title}** chamou atenção no mundo de {pt_label.lower()} "
                f"hoje."
            )

        ctx_pt: list[str] = []
        if tags_str:
            ctx_pt.append(f"Tags: {tags_str}")
        if author_str:
            ctx_pt.append(f"Autor: **{author_str}**")
        if ctx_pt:
            parts_pt.append(" · ".join(ctx_pt))

        signal_pt: list[str] = []
        if score_str:
            signal_pt.append(f"**{score_str}** pontos")
        if a.comments_count:
            signal_pt.append(f"**{a.comments_count}** comentários")
        signal_pt.append(f"via **{source_label}**")

        parts_pt.append(
            "Repercussão: " + ", ".join(signal_pt) + ". "
            "Confira a fonte original abaixo para a matéria completa."
        )

        body_pt = "\n\n".join(parts_pt)

        sources = [{"title": a.title, "url": a.url, "source": a.source}]

        digest.append(
            {
                "title_en": title,
                "title_pt": title,
                "body_en": body_en,
                "body_pt": body_pt,
                "category": cat,
                "emoji": emoji,
                "sources": sources,
            }
        )

    logger.info(
        "Fallback digest: %d entries from %d articles", len(digest), len(articles)
    )
    return digest
