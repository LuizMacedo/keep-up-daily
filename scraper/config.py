"""Configuration for keep-up-daily scraper."""

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
WEB_DIR = PROJECT_ROOT / "web"

# ---------------------------------------------------------------------------
# HTTP / request settings
# ---------------------------------------------------------------------------
REQUEST_TIMEOUT = 30  # seconds
USER_AGENT = "KeepUpDaily/1.0 (https://github.com/LuizMacedo/keep-up-daily)"
REQUEST_DELAY = 1.0  # seconds between requests to same host

# ---------------------------------------------------------------------------
# Data retention
# ---------------------------------------------------------------------------
RETENTION_DAYS = 30

# ---------------------------------------------------------------------------
# Source configuration
# ---------------------------------------------------------------------------
SOURCES = {
    "devto": {
        "enabled": True,
        "max_articles": 30,
    },
    "hackernews": {
        "enabled": True,
        "max_articles": 30,
    },
    "github_trending": {
        "enabled": True,
        "languages": ["", "python", "javascript", "typescript", "rust", "go"],
    },
    "reddit": {
        "enabled": True,
        "subreddits": [
            "programming",
            "webdev",
            "machinelearning",
            "devops",
            "python",
            "rust",
            "golang",
            "javascript",
            "reactjs",
            "node",
            "cpp",
        ],
        "max_per_subreddit": 10,
    },
    "lobsters": {
        "enabled": True,
        "max_articles": 25,
    },
    "hashnode": {
        "enabled": True,
        "max_articles": 20,
    },
}

# ---------------------------------------------------------------------------
# Category definitions (used by categorizer)
# ---------------------------------------------------------------------------
CATEGORIES = {
    "ai": {
        "label_en": "AI & ML",
        "label_pt": "IA & ML",
        "keywords": [
            "artificial intelligence", "machine learning", "deep learning",
            "neural network", "gpt", "llm", "transformer", "nlp",
            "computer vision", "openai", "anthropic", "gemini", "claude",
            "chatgpt", "stable diffusion", "midjourney", "copilot ai",
            "langchain", "hugging face", "huggingface", "pytorch",
            "tensorflow", "reinforcement learning", "generative ai",
            "diffusion model", "embedding", "vector database", "rag",
            "fine-tuning", "fine tuning", "lora", "mistral", "llama",
            "attention mechanism", "ai agent", "mcp server",
        ],
    },
    "web": {
        "label_en": "Web Dev",
        "label_pt": "Desenvolvimento Web",
        "keywords": [
            "react", "vue", "angular", "svelte", "next.js", "nextjs",
            "nuxt", "frontend", "front-end", "css", "html", "javascript",
            "typescript", "web development", "browser", "dom", "webpack",
            "vite", "tailwind", "node.js", "nodejs", "deno", "bun",
            "remix", "astro", "solid.js", "qwik", "htmx",
            "web component", "pwa", "responsive design", "accessibility",
            "a11y", "wasm", "webassembly", "web api", "service worker",
        ],
    },
    "devops": {
        "label_en": "DevOps & Cloud",
        "label_pt": "DevOps & Nuvem",
        "keywords": [
            "docker", "kubernetes", "k8s", "ci/cd", "pipeline", "terraform",
            "aws", "azure", "gcp", "cloud computing", "devops", "jenkins",
            "github actions", "monitoring", "observability", "infrastructure",
            "ansible", "helm", "argocd", "prometheus", "grafana",
            "serverless", "lambda", "container", "microservice",
            "load balancer", "cdn", "nginx", "linux server",
            "sre", "site reliability", "incident response", "platform engineering",
        ],
    },
    "languages": {
        "label_en": "Languages",
        "label_pt": "Linguagens",
        "keywords": [
            "python", "rust lang", "rustlang", "golang", "go language",
            "java ", "kotlin", "swift", "c\\+\\+", "cpp", "c#", "csharp",
            "ruby", "elixir", "scala", "haskell", "zig", "nim", "ocaml",
            "clojure", "erlang", "f#", "fsharp", "lua", "julia",
            "programming language", "compiler", "interpreter", "type system",
            "memory management", "garbage collection", "concurrency model",
        ],
    },
    "frameworks": {
        "label_en": "Frameworks",
        "label_pt": "Frameworks",
        "keywords": [
            "django", "flask", "fastapi", "spring boot", "rails",
            "laravel", "express.js", "nestjs", "framework", "library",
            "sdk", "graphql", "rest api", "grpc", "trpc", "prisma",
            "sqlalchemy", "orm", "database", "postgresql", "mysql",
            "mongodb", "redis", "sqlite", "supabase", "firebase",
            "drizzle", "effect-ts", "actix", "axum", "gin", "echo",
        ],
    },
    "security": {
        "label_en": "Security",
        "label_pt": "Segurança",
        "keywords": [
            "security", "vulnerability", "cve", "exploit", "encryption",
            "authentication", "oauth", "zero-day", "zero day", "malware",
            "ransomware", "cybersecurity", "penetration testing", "pentest",
            "xss", "sql injection", "csrf", "cors", "ssl", "tls",
            "certificate", "firewall", "vpn", "audit", "compliance",
            "supply chain attack", "backdoor",
        ],
    },
    "career": {
        "label_en": "Career",
        "label_pt": "Carreira",
        "keywords": [
            "career", "interview", "salary", "remote work", "job market",
            "hiring", "engineering culture", "management", "leadership",
            "burnout", "productivity", "mentoring", "open source",
            "community", "conference", "tutorial", "learning path",
            "beginner guide", "senior engineer", "staff engineer",
            "tech lead", "freelance", "startup", "side project",
        ],
    },
}

DEFAULT_CATEGORY = "general"

# ---------------------------------------------------------------------------
# AI Curation (GitHub Models API)
# ---------------------------------------------------------------------------
AI_CONFIG = {
    "enabled": True,
    "endpoint": "https://models.inference.ai.azure.com/chat/completions",
    "model": "gpt-4o-mini",
    "temperature": 0.4,
    "max_entries": 30,          # upper ceiling – AI decides actual count
    "fallback_per_cat": 4,     # top articles per category for fallback
    "request_timeout": 180,     # seconds – richer digest needs more time
}
