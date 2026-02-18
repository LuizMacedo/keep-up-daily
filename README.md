<div align="center">

# 📰 Keep Up Daily

**A free, automated, daily-curated tech feed for developers who never stop learning.**

[![Daily Feed](https://github.com/LuizMacedo/keep-up-daily/actions/workflows/deploy.yml/badge.svg)](https://github.com/LuizMacedo/keep-up-daily/actions/workflows/deploy.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![GitHub Pages](https://img.shields.io/badge/dashboard-live-brightgreen)](https://luizmacedo.github.io/keep-up-daily/)

[**📖 Read the Dashboard →**](https://luizmacedo.github.io/keep-up-daily/)

</div>

---

## What is this?

**Keep Up Daily** is a Python-powered web scraper that automatically collects trending tech articles, tutorials, and repositories every single day — and publishes them as a clean, distraction-free reading dashboard on GitHub Pages.

No ads. No tracking. No monetization. Just pure learning content.

### Sources

| Source              | Type          | What it captures                         |
| ------------------- | ------------- | ---------------------------------------- |
| **Dev.to**          | REST API      | Top community articles                   |
| **Hacker News**     | Firebase API  | Top stories                              |
| **GitHub Trending** | HTML scraping | Daily trending repositories              |
| **Reddit**          | JSON API      | Hot posts from 11 programming subreddits |
| **Lobste.rs**       | JSON API      | Hottest tech stories                     |
| **Hashnode**        | GraphQL API   | Best developer blog posts                |

### Categories

Content is automatically categorized into: **AI & ML**, **Web Dev**, **DevOps & Cloud**, **Languages**, **Frameworks**, **Security**, **Career**, and **General**.

---

## Dashboard Features

- **Clean, focused reading experience** — zero distractions, content-first design
- **Category filter tabs** — focus on what matters to you
- **Full-text search** — instantly filter across all articles
- **Date navigation** — browse up to 30 days of history
- **Dark mode** — respects your system preference, toggleable
- **Bilingual UI** — English 🇺🇸 and Portuguese 🇧🇷
- **Fully responsive** — works on desktop, tablet, and mobile
- **No JavaScript frameworks** — fast, lightweight vanilla JS + TailwindCSS

---

## Project Structure

```
keep-up-daily/
├── .github/workflows/
│   └── deploy.yml          # Daily cron + GitHub Pages deployment
├── scraper/
│   ├── __init__.py
│   ├── __main__.py          # python -m scraper entrypoint
│   ├── main.py              # Orchestrator
│   ├── config.py            # All configuration in one place
│   ├── categorizer.py       # Keyword-based categorization
│   ├── output.py            # JSON output + data retention
│   └── sources/
│       ├── __init__.py      # Exports ALL_SCRAPERS list
│       ├── base.py          # Article dataclass + BaseScraper
│       ├── devto.py
│       ├── hackernews.py
│       ├── github_trending.py
│       ├── reddit.py
│       ├── lobsters.py
│       └── hashnode.py
├── web/
│   ├── index.html           # Dashboard (TailwindCSS)
│   └── app.js               # Vanilla JS app logic + i18n
├── data/                    # Auto-generated JSON (one file per day)
├── requirements.txt
├── LICENSE
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- pip

### Run Locally

```bash
# Clone the repository
git clone https://github.com/LuizMacedo/keep-up-daily.git
cd keep-up-daily

# Install dependencies
pip install -r requirements.txt

# Run the scraper
python -m scraper

# Output will be in data/YYYY-MM-DD.json
```

To preview the dashboard locally, serve the `web/` folder plus `data/`:

```bash
# Quick local preview
mkdir -p /tmp/kud-preview/data
cp web/* /tmp/kud-preview/
cp data/*.json /tmp/kud-preview/data/ 2>/dev/null
cd /tmp/kud-preview && python -m http.server 8000
# Open http://localhost:8000
```

### Automated (via GitHub Actions)

Once pushed to GitHub, the workflow runs automatically:

- **Every day at 8:00 AM Central Time (14:00 UTC)**
- Can also be triggered manually: _Actions → Keep Up Daily → Run workflow_
- Scrapes all sources, commits data, and deploys to GitHub Pages

---

## Enabling GitHub Pages

To activate the dashboard on your fork:

1. Go to your repository **Settings** → **Pages**
2. Under **Build and deployment**, set **Source** to **GitHub Actions**
3. Trigger the workflow manually (Actions → Keep Up Daily → Run workflow)
4. Your dashboard will be live at `https://<your-username>.github.io/keep-up-daily/`

> **Important:** You must select **"GitHub Actions"** as the source, not "Deploy from a branch".

---

## How to Fork & Personalize

This project is designed to be forked and customized. Here's how:

### 1. Fork the repository

Click the **Fork** button at the top of this page.

### 2. Enable GitHub Pages

Follow the instructions above to set the source to "GitHub Actions".

### 3. Customize sources

Edit `scraper/config.py`:

```python
# Add/remove subreddits
SOURCES["reddit"]["subreddits"] = ["programming", "rust", "your_favorite_sub"]

# Disable a source
SOURCES["hashnode"]["enabled"] = False

# Add more GitHub Trending languages
SOURCES["github_trending"]["languages"] = ["", "python", "rust", "zig"]
```

### 4. Customize categories

Edit the `CATEGORIES` dictionary in `scraper/config.py` to add keywords for topics you care about.

### 5. Add a new source

Create a new file in `scraper/sources/` following this pattern:

```python
# scraper/sources/my_source.py
from .base import Article, BaseScraper

class MySourceScraper(BaseScraper):
    name = "my_source"

    def fetch(self) -> list[Article]:
        articles = []
        # Your scraping logic here...
        # Return a list of Article objects
        return articles
```

Then register it in `scraper/sources/__init__.py`:

```python
from .my_source import MySourceScraper

ALL_SCRAPERS = [
    # ...existing scrapers...
    MySourceScraper,
]
```

---

## Contributing

Contributions are welcome! This project is meant to help the developer community learn and grow.

### For New Contributors

1. **Fork** the repository
2. Create a feature branch: `git checkout -b feature/my-improvement`
3. Make your changes
4. Run the scraper locally to test: `python -m scraper`
5. Commit with a clear message: `git commit -m "Add: new source scraper for XYZ"`
6. Push and open a **Pull Request**

### Ideas for Contributions

- 🌐 **New sources** — add scrapers for tech newsletters, podcasts, YouTube channels
- 🏷️ **Better categorization** — improve keyword matching or add ML-based classification
- 🌍 **More languages** — add UI translations beyond EN/PT
- 📊 **Analytics** — weekly trends, most popular topics, source comparison
- 🎨 **UI improvements** — accessibility, animations, reading progress
- 📱 **PWA support** — offline reading, push notifications
- 🧪 **Tests** — unit tests for scrapers and categorizer

### For Experienced Developers

The codebase follows a modular architecture. Each source scraper is independent and follows the `BaseScraper` interface. The `Article` dataclass is the normalized schema. Feel free to refactor, optimize, or propose architectural changes.

---

## How It Works

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Dev.to     │     │              │     │  Categorize │
│  HackerNews │────▶│  Orchestrator│────▶│  Deduplicate│
│  GitHub     │     │  (main.py)   │     │  Sort       │
│  Reddit     │     │              │     │             │
│  Lobsters   │     └──────────────┘     └──────┬──────┘
│  Hashnode   │                                  │
└─────────────┘                                  ▼
                                          ┌─────────────┐
                                          │ data/       │
                                          │ YYYY-MM-DD  │
                                          │ .json       │
                                          └──────┬──────┘
                                                 │
                                          ┌──────▼──────┐
                                          │ GitHub Pages│
                                          │ Dashboard   │
                                          └─────────────┘
```

**Daily at 14:00 UTC**, GitHub Actions:

1. Runs all scrapers in sequence (with error isolation)
2. Deduplicates articles by URL
3. Categorizes using keyword matching
4. Sorts by engagement score
5. Saves to `data/YYYY-MM-DD.json`
6. Commits and pushes data
7. Builds and deploys the static dashboard

---

## Philosophy

> "The best time to start learning was yesterday. The second best time is today."

This project exists because:

- **Staying current** in tech is overwhelming — there are too many sources to check
- **Curated feeds** shouldn't cost money or track you
- **Open source tools** should make learning accessible to everyone
- **Community-driven** means everyone benefits from everyone's contributions

---

## License

MIT — use it however you want. See [LICENSE](LICENSE) for details.

---

<div align="center">

**Made with ❤️ for the developer community**

_If this helps you learn something new, consider sharing it with a fellow developer._

⭐ Star this repo if you find it useful!

</div>
