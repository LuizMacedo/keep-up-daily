/**
 * Keep Up Daily — Daily Developer Digest
 * Zero-dependency vanilla JS.  Renders AI-curated digest entries.
 */

// ──────────────────────────────────────────────
// I18N
// ──────────────────────────────────────────────
const I18N = {
    en: {
        title: "Keep Up Daily",
        subtitle: "Your daily developer digest",
        all: "All",
        ai: "AI & ML",
        web: "Web Dev",
        devops: "DevOps & Cloud",
        languages: "Languages",
        frameworks: "Frameworks",
        security: "Security",
        career: "Career",
        general: "General",
        stories: "stories",
        curatedFrom: "curated from",
        articles: "articles",
        sources: "sources",
        deepDive: "Deep dive →",
        searchPlaceholder: "Search digest…",
        noDataTitle: "No digest yet",
        noDataDesc:
            "The digest is generated daily at 8:00 AM CT. You can also trigger it manually from GitHub Actions.",
        noMatch: "No entries match your filter.",
        prev: "Previous day",
        next: "Next day",
        footerBuilt: "Built for developers who never stop learning.",
        footerFree: "100% free, zero ads, open source.",
        readTime: "min read",
    },
    pt: {
        title: "Keep Up Daily",
        subtitle: "Seu resumo diário de tecnologia",
        all: "Todos",
        ai: "IA & ML",
        web: "Desenvolvimento Web",
        devops: "DevOps & Nuvem",
        languages: "Linguagens",
        frameworks: "Frameworks",
        security: "Segurança",
        career: "Carreira",
        general: "Geral",
        stories: "histórias",
        curatedFrom: "curadas de",
        articles: "artigos",
        sources: "fontes",
        deepDive: "Aprofunde-se →",
        searchPlaceholder: "Buscar no resumo…",
        noDataTitle: "Nenhum resumo ainda",
        noDataDesc:
            "O resumo é gerado diariamente às 8:00 AM CT. Você também pode acioná-lo manualmente pelo GitHub Actions.",
        noMatch: "Nenhuma entrada corresponde ao filtro.",
        prev: "Dia anterior",
        next: "Próximo dia",
        footerBuilt: "Feito para devs que nunca param de aprender.",
        footerFree: "100% gratuito, zero anúncios, open source.",
        readTime: "min de leitura",
    },
};

// Source display
const SOURCE_META = {
    devto: { label: "Dev.to", color: "#3b49df" },
    hackernews: { label: "Hacker News", color: "#ff6600" },
    github_trending: { label: "GitHub", color: "#8b5cf6" },
    reddit: { label: "Reddit", color: "#ff4500" },
    lobsters: { label: "Lobsters", color: "#ac130d" },
    hashnode: { label: "Hashnode", color: "#2962ff" },
};

const CATEGORIES = [
    "all", "ai", "web", "devops", "languages",
    "frameworks", "security", "career", "general",
];

// ──────────────────────────────────────────────
// STATE
// ──────────────────────────────────────────────
let state = {
    lang: localStorage.getItem("kud-lang") || "en",
    dark:
        localStorage.getItem("kud-dark") === "true" ||
        (!localStorage.getItem("kud-dark") &&
            window.matchMedia("(prefers-color-scheme: dark)").matches),
    dates: [],
    currentIdx: 0,
    digest: [],
    rawCount: 0,
    sourcesUsed: [],
    activeCategory: "all",
    searchQuery: "",
};

// ──────────────────────────────────────────────
// HELPERS
// ──────────────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const t = (key) => I18N[state.lang]?.[key] || I18N.en[key] || key;

function formatDate(iso) {
    const d = new Date(iso + "T12:00:00");
    return d.toLocaleDateString(state.lang === "pt" ? "pt-BR" : "en-US", {
        weekday: "long",
        year: "numeric",
        month: "long",
        day: "numeric",
    });
}

function escapeHtml(str) {
    const el = document.createElement("span");
    el.textContent = str;
    return el.innerHTML;
}

function estimateReadTime(text) {
    const words = (text || "").split(/\s+/).length;
    return Math.max(1, Math.ceil(words / 200));
}

/**
 * Markdown → HTML for digest bodies.
 * Handles: paragraphs, **bold**, *italic*, `code`, bullet/numbered lists,
 * ### headings, and --- horizontal rules.
 */
function renderMarkdown(text) {
    if (!text) return "";
    const blocks = text.split(/\n\n+/);
    return blocks
        .map((block) => {
            block = block.trim();
            if (!block) return "";

            // Horizontal rule
            if (/^[-*_]{3,}$/.test(block)) {
                return '<hr class="my-4 border-gray-200 dark:border-slate-700">';
            }

            // Heading (### or ##)
            const headingMatch = block.match(/^(#{2,4})\s+(.+)$/);
            if (headingMatch) {
                const level = headingMatch[1].length;
                let content = escapeHtml(headingMatch[2]);
                content = inlineFormat(content);
                const cls = level <= 2 ? 'text-lg font-bold mt-3 mb-1' : 'text-base font-semibold mt-2 mb-1';
                return `<h${level + 1} class="${cls}">${content}</h${level + 1}>`;
            }

            // Bullet or numbered list
            const lines = block.split("\n");
            const isBullet = lines.every((l) => /^\s*[-•●*]\s/.test(l));
            const isNumbered = lines.every((l) => /^\s*\d+[.)]\s/.test(l));

            if (isBullet || isNumbered) {
                const tag = isNumbered ? 'ol' : 'ul';
                const cls = isNumbered
                    ? 'list-decimal list-inside space-y-1.5 ml-1'
                    : 'list-disc list-inside space-y-1.5 ml-1';
                const items = lines
                    .map((l) => {
                        let c = l.replace(/^\s*[-•●*]\s*/, '').replace(/^\s*\d+[.)]\s*/, '');
                        c = inlineFormat(escapeHtml(c));
                        return `<li class="leading-relaxed">${c}</li>`;
                    })
                    .join("");
                return `<${tag} class="${cls}">${items}</${tag}>`;
            }

            // Regular paragraph
            let html = escapeHtml(block);
            html = inlineFormat(html);
            html = html.replace(/\n/g, "<br>");
            return `<p class="leading-relaxed">${html}</p>`;
        })
        .filter(Boolean)
        .join("");
}

/** Apply inline markdown formatting: bold, italic, code */
function inlineFormat(html) {
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/(?<!\*)\*([^*]+?)\*(?!\*)/g, '<em>$1</em>');
    html = html.replace(/`([^`]+?)`/g,
        '<code class="text-sm px-1.5 py-0.5 rounded bg-gray-100 dark:bg-slate-800 text-brand-700 dark:text-brand-400 font-mono">$1</code>');
    return html;
}

// ──────────────────────────────────────────────
// DARK MODE
// ──────────────────────────────────────────────
function applyDark() {
    document.documentElement.classList.toggle("dark", state.dark);
    localStorage.setItem("kud-dark", state.dark);
}

// ──────────────────────────────────────────────
// I18N DOM
// ──────────────────────────────────────────────
function applyI18n() {
    document.querySelectorAll("[data-i18n]").forEach((el) => {
        const key = el.dataset.i18n;
        if (I18N[state.lang]?.[key]) el.textContent = I18N[state.lang][key];
    });
    $("#search-input").placeholder = t("searchPlaceholder");
    document.documentElement.lang = state.lang === "pt" ? "pt-BR" : "en";
}

// ──────────────────────────────────────────────
// DATA
// ──────────────────────────────────────────────
async function fetchIndex() {
    try {
        const r = await fetch("./data/index.json");
        if (!r.ok) return [];
        return (await r.json()).available_dates || [];
    } catch {
        return [];
    }
}

async function fetchDay(dateStr) {
    try {
        const r = await fetch(`./data/${dateStr}.json`);
        if (!r.ok) return null;
        return await r.json();
    } catch {
        return null;
    }
}

// ──────────────────────────────────────────────
// RENDER: CATEGORY BAR
// ──────────────────────────────────────────────
function renderCategoryBar() {
    const bar = $("#category-bar");
    bar.innerHTML = "";

    CATEGORIES.forEach((cat) => {
        const btn = document.createElement("button");
        btn.className =
            "cat-pill px-3 py-1.5 text-xs font-medium rounded-full whitespace-nowrap transition " +
            (state.activeCategory === cat
                ? "bg-brand-600 text-white active"
                : "bg-gray-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-gray-200 dark:hover:bg-slate-700");
        btn.textContent = t(cat);
        btn.addEventListener("click", () => {
            state.activeCategory = cat;
            renderCategoryBar();
            renderDigest();
        });
        bar.appendChild(btn);
    });
}

// ──────────────────────────────────────────────
// RENDER: DIGEST ENTRIES
// ──────────────────────────────────────────────
function renderDigest() {
    const list = $("#digest-list");
    const empty = $("#empty-state");
    const noMatch = $("#no-match-state");
    const loading = $("#loading-state");

    loading.classList.add("hidden");

    if (!state.digest.length) {
        list.innerHTML = "";
        empty.classList.remove("hidden");
        noMatch.classList.add("hidden");
        return;
    }
    empty.classList.add("hidden");

    const q = state.searchQuery.toLowerCase();
    const filtered = state.digest.filter((entry) => {
        const catOk =
            state.activeCategory === "all" || entry.category === state.activeCategory;
        const title = (
            state.lang === "pt" ? entry.title_pt : entry.title_en || ""
        ).toLowerCase();
        const body = (
            state.lang === "pt" ? entry.body_pt : entry.body_en || ""
        ).toLowerCase();
        const searchOk = !q || title.includes(q) || body.includes(q);
        return catOk && searchOk;
    });

    if (!filtered.length) {
        list.innerHTML = "";
        noMatch.classList.remove("hidden");
        return;
    }
    noMatch.classList.add("hidden");

    list.innerHTML = filtered
        .map((entry, idx) => {
            const title =
                state.lang === "pt" ? entry.title_pt : entry.title_en;
            const body =
                state.lang === "pt" ? entry.body_pt : entry.body_en;
            const catLabel = t(entry.category || "general");
            const bodyHtml = renderMarkdown(body || "");
            const readMin = estimateReadTime(body || "");

            // Source links
            const sourcesHtml = (entry.sources || [])
                .map((s) => {
                    const meta = SOURCE_META[s.source] || {
                        label: s.source,
                        color: "#6b7280",
                    };
                    const label =
                        s.title.length > 70 ? s.title.slice(0, 67) + "…" : s.title;
                    return `<a href="${escapeHtml(s.url)}" target="_blank" rel="noopener noreferrer"
                     class="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400 hover:text-brand-600 dark:hover:text-brand-400 transition group">
                    <span class="w-1.5 h-1.5 rounded-full flex-shrink-0" style="background:${meta.color}"></span>
                    <span class="group-hover:underline">${escapeHtml(label)}</span>
                    <span class="text-[11px] opacity-60">${escapeHtml(meta.label)}</span>
                  </a>`;
                })
                .join("");

            return `
      <article class="digest-entry bg-white dark:bg-slate-900 rounded-2xl border border-gray-200 dark:border-slate-800 p-6 sm:p-8">
        <div class="flex items-center gap-2.5 mb-4 flex-wrap">
          <span class="text-2xl leading-none" aria-hidden="true">${entry.emoji || "📌"}</span>
          <span class="text-xs font-semibold px-2.5 py-1 rounded-full bg-brand-50 dark:bg-brand-600/20 text-brand-700 dark:text-brand-400">
            ${escapeHtml(catLabel)}
          </span>
          <span class="text-xs text-slate-400 dark:text-slate-500 ml-auto">
            ${readMin} ${t("readTime")}
          </span>
        </div>
        <h2 class="text-xl sm:text-2xl font-bold leading-snug mb-4 text-slate-900 dark:text-white">
          ${escapeHtml(title)}
        </h2>
        <div class="prose-body text-[15px] leading-relaxed text-slate-700 dark:text-slate-300 space-y-3 mb-5">
          ${bodyHtml}
        </div>
        ${entry.sources && entry.sources.length
                    ? `<div class="pt-4 border-t border-gray-100 dark:border-slate-800">
                <p class="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-2.5">
                  ${t("deepDive")}
                </p>
                <div class="flex flex-col gap-1.5">${sourcesHtml}</div>
              </div>`
                    : ""
                }
      </article>`;
        })
        .join("");
}

// ──────────────────────────────────────────────
// RENDER: STATS + DATE NAV
// ──────────────────────────────────────────────
function renderStats(dayData) {
    const el = $("#stats-count");
    if (!dayData) {
        el.textContent = "";
        return;
    }
    const digestN = (dayData.digest || []).length;
    const rawN = dayData.raw_article_count || dayData.total_articles || 0;
    const srcN = (dayData.sources || dayData.sources_used || []).length;
    el.textContent = `${digestN} ${t("stories")} · ${t("curatedFrom")} ${rawN} ${t("articles")} · ${srcN} ${t("sources")}`;
}

function renderDateNav() {
    const dateEl = $("#current-date");
    const prevBtn = $("#date-prev");
    const nextBtn = $("#date-next");

    if (!state.dates.length) {
        dateEl.textContent = formatDate(new Date().toISOString().slice(0, 10));
        prevBtn.disabled = true;
        nextBtn.disabled = true;
        return;
    }

    dateEl.textContent = formatDate(state.dates[state.currentIdx]);
    prevBtn.disabled = state.currentIdx >= state.dates.length - 1;
    nextBtn.disabled = state.currentIdx <= 0;
}

async function navigateDate(delta) {
    const newIdx = state.currentIdx - delta; // dates newest-first
    if (newIdx < 0 || newIdx >= state.dates.length) return;
    state.currentIdx = newIdx;
    await loadDay();
}

// ──────────────────────────────────────────────
// MAIN LOAD
// ──────────────────────────────────────────────
async function loadDay() {
    const list = $("#digest-list");
    const empty = $("#empty-state");
    const noMatch = $("#no-match-state");
    const loading = $("#loading-state");

    list.innerHTML = "";
    empty.classList.add("hidden");
    noMatch.classList.add("hidden");
    loading.classList.remove("hidden");
    renderDateNav();

    if (!state.dates.length) {
        loading.classList.add("hidden");
        empty.classList.remove("hidden");
        renderStats(null);
        return;
    }

    const dayData = await fetchDay(state.dates[state.currentIdx]);
    if (!dayData) {
        state.digest = [];
        loading.classList.add("hidden");
        empty.classList.remove("hidden");
        renderStats(null);
        return;
    }

    state.digest = dayData.digest || [];
    state.rawCount = dayData.raw_article_count || 0;
    state.sourcesUsed = dayData.sources || [];
    renderStats(dayData);
    renderDigest();
}

// ──────────────────────────────────────────────
// INIT
// ──────────────────────────────────────────────
async function init() {
    applyDark();

    $("#dark-toggle").addEventListener("click", () => {
        state.dark = !state.dark;
        applyDark();
    });

    $("#lang-toggle").addEventListener("click", () => {
        state.lang = state.lang === "en" ? "pt" : "en";
        localStorage.setItem("kud-lang", state.lang);
        $("#lang-toggle").textContent = state.lang.toUpperCase();
        applyI18n();
        renderCategoryBar();
        renderDateNav();
        renderDigest();
        if (state.dates.length) {
            fetchDay(state.dates[state.currentIdx]).then(renderStats);
        }
    });

    $("#date-prev").addEventListener("click", () => navigateDate(-1));
    $("#date-next").addEventListener("click", () => navigateDate(1));

    let searchTimer;
    $("#search-input").addEventListener("input", (e) => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => {
            state.searchQuery = e.target.value;
            renderDigest();
        }, 200);
    });

    $("#lang-toggle").textContent = state.lang.toUpperCase();
    applyI18n();
    renderCategoryBar();

    state.dates = await fetchIndex();
    state.currentIdx = 0;
    await loadDay();
}

document.addEventListener("DOMContentLoaded", init);
