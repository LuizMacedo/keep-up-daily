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

# GitHub Models free-tier limits: ~8 000 input tokens for gpt-4o-mini.
# We keep a safe margin and progressively reduce if we hit 413.
_MAX_AI_ARTICLES = 30          # first attempt
_MAX_AI_ARTICLES_RETRY = 15    # retry with fewer articles
_DESC_MAX_CHARS = 120          # trim descriptions to save tokens
_MAX_OUTPUT_TOKENS = 6144      # enough room for 10-12 entries

# Token env var – ONLY GH_MODELS_TOKEN works with GitHub Models API.
# The automatic GITHUB_TOKEN (${{ github.token }}) does NOT have access to
# models.inference.ai.azure.com and would silently cause a 401 error.
_TOKEN_VAR = "GH_MODELS_TOKEN"


def _get_token() -> str:
    """Return the GH_MODELS_TOKEN if set, otherwise empty string."""
    val = os.environ.get(_TOKEN_VAR, "").strip()
    if val:
        print(f"[AI] ✓ Found ${_TOKEN_VAR} ({len(val)} chars)")
        logger.info("Using token from $%s (%d chars)", _TOKEN_VAR, len(val))
        return val
    print(f"[AI] ✗ ${_TOKEN_VAR} not set or empty — AI digest disabled")
    logger.warning("$%s not set or empty", _TOKEN_VAR)
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

    if not AI_CONFIG["enabled"]:
        print("[AI] AI curation is disabled in config")
        logger.warning("AI digest disabled in config – using fallback")
        return _fallback_digest(articles)

    if not token:
        print(f"[AI] No ${_TOKEN_VAR} found – using fallback digest")
        logger.warning("No $%s found – using fallback digest", _TOKEN_VAR)
        return _fallback_digest(articles)

    # Select top articles to stay within GitHub Models token limits
    selected = _select_top_articles(articles, _MAX_AI_ARTICLES)
    print(f"[AI] Selected {len(selected)} top articles from {len(articles)} total")

    condensed = _condense_articles(selected)
    digest = _call_ai(condensed, selected, token)

    # Retry with fewer articles if first attempt returned nothing
    # (likely a 413 / token-limit error)
    if not digest and len(selected) > _MAX_AI_ARTICLES_RETRY:
        retry_selected = _select_top_articles(articles, _MAX_AI_ARTICLES_RETRY)
        print(f"[AI] Retrying with {len(retry_selected)} articles …")
        condensed = _condense_articles(retry_selected)
        digest = _call_ai(condensed, retry_selected, token)

    if not digest:
        print("[AI] ✗ AI returned nothing – falling back to score-based digest")
        logger.warning("AI returned nothing – falling back")
        return _fallback_digest(articles)

    print(f"[AI] ✓ AI digest complete: {len(digest)} entries from {len(articles)} articles")
    logger.info(
        "AI digest complete: %d entries from %d articles", len(digest), len(articles)
    )
    return digest


# ──────────────────────────────────────────────────
# AI call
# ──────────────────────────────────────────────────
def _select_top_articles(
    articles: list[Article], max_count: int
) -> list[Article]:
    """Pick the top articles by score, diversified across categories.

    Round-robin from each category so the digest covers a broad range.
    """
    by_cat: dict[str, list[Article]] = defaultdict(list)
    for a in articles:
        by_cat[a.category].append(a)

    for cat in by_cat:
        by_cat[cat].sort(key=lambda x: x.score, reverse=True)

    selected: list[Article] = []
    cat_keys = sorted(by_cat.keys())
    idx = 0
    while len(selected) < max_count:
        added = False
        for cat in cat_keys:
            if idx < len(by_cat[cat]) and len(selected) < max_count:
                selected.append(by_cat[cat][idx])
                added = True
        idx += 1
        if not added:
            break
    return selected


def _condense_articles(articles: list[Article]) -> list[dict]:
    """Compact representation for the AI — kept small for token budget."""
    return [
        {
            "id": idx,
            "title": a.title,
            "source": a.source,
            "category": a.category,
            "desc": (a.description or "")[:_DESC_MAX_CHARS],
            "score": a.score,
            "tags": a.tags[:4],
            "comments": a.comments_count,
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

    prompt = f"""You have {len(condensed)} tech articles scraped today.
Categories: {cat_summary}

Create a developer daily digest. Write 10-12 entries (one per interesting topic).
Merge related articles into a single entry.

Each entry is a SELF-CONTAINED mini-article (120-180 words per language).
Structure: lead (why care?), technical depth (how it works, key details, trade-offs),
practical angle (when to use it), and a punchy takeaway.

Rules:
- Be specific: library names, benchmarks, architecture details
- Use **bold** for key terms, `code` for technical names
- Cover at least 4 different categories
- Write English AND Brazilian Portuguese (natural, not translated)

For EACH entry return:
- title_en, title_pt: specific headline
- body_en, body_pt: the mini-article
- category: ai|web|devops|languages|frameworks|security|career|general
- source_ids: array of article IDs used

Articles:
{json.dumps(condensed, ensure_ascii=False)}

Respond with ONLY a JSON array:
[{{"title_en":"...","title_pt":"...","body_en":"...","body_pt":"...","category":"...","source_ids":[0,3]}}]"""

    prompt_chars = len(prompt)
    print(f"[AI] Sending {len(condensed)} articles to Models API (~{prompt_chars // 4} est. tokens)")

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
                            "You are a senior tech journalist writing a developer "
                            "newsletter. Each entry is a self-contained mini-article "
                            "with technical depth. Write English and Brazilian "
                            "Portuguese. Respond ONLY with valid JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": TEMPERATURE,
                "max_tokens": _MAX_OUTPUT_TOKENS,
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
        print(f"[AI] ✗ HTTP {code} from Models API — {body[:200]}")
        logger.error("AI HTTP %s: %s | body: %s", code, exc, body)
    except json.JSONDecodeError as exc:
        print(f"[AI] ✗ AI returned invalid JSON: {exc}")
        logger.error("AI returned invalid JSON: %s", exc)
    except requests.exceptions.Timeout:
        print(f"[AI] ✗ Request timed out after {TIMEOUT}s")
        logger.error("AI request timed out after %ds", TIMEOUT)
    except requests.exceptions.ConnectionError as exc:
        print(f"[AI] ✗ Connection error: {exc}")
        logger.error("AI connection error: %s", exc)
    except Exception as exc:
        print(f"[AI] ✗ Unexpected error: {type(exc).__name__}: {exc}")
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
