# Reddit Monitor — Self-Hosted Brand Intelligence

Turn Reddit into competitive intelligence. Monitor brand mentions, analyze competitor sentiment, and get AI-powered strategic reports — all running free on GitHub Actions.

## What It Does

1. **Scans Reddit** for your brand, competitors, and industry keywords
2. **Fetches comments** from high-engagement posts
3. **Analyzes everything** with Claude AI for strategic insights
4. **Delivers reports** via email and a GitHub Pages dashboard

Reports include: brand perception, competitive landscape, market insights, pain points, recommendation patterns, threats, and actionable recommendations — all with Reddit quotes and data.

---

## Quick Start (5 minutes)

### 1. Fork this repo

Click **Fork** at the top right of this page.

### 2. Edit `config.toml`

In your fork, click `config.toml` → pencil icon → replace with your brand info:

```toml
[brand]
name = "Your Brand"
aliases = ["your brand", "yourbrand.com"]

[competitors]
names = ["competitor1", "competitor2", "competitor3"]

[subreddits]
high_value = ["yoursubreddit", "yourindustry"]

[keywords]
relevance = ["your industry", "your product type"]
geographic = ["your region"]
```

See `config.example.toml` for a full example with all options.

### 3. Add your API key

Go to **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Value |
|--------|-------|
| `ANTHROPIC_API_KEY` | Your key from [console.anthropic.com](https://console.anthropic.com/) |

**Cost:** ~$0.14 per run with Sonnet (~$3/month at daily usage).

### 4. Set up email delivery (optional)

Add these secrets the same way:

| Secret | Example |
|--------|---------|
| `SMTP_SERVER` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USERNAME` | `you@gmail.com` |
| `SMTP_PASSWORD` | Your [app password](https://myaccount.google.com/apppasswords) (not regular password) |
| `EMAIL_RECIPIENTS` | `you@gmail.com, team@company.com` |

### 5. Enable GitHub Pages & Actions

**Pages:** Settings → Pages → Source: Deploy from branch → `main` / `/docs` → Save

**Actions:** Actions tab → "I understand my workflows, go ahead and enable them"

### 6. Run it

Actions tab → **Reddit Monitor** → **Run workflow** → choose `daily` → **Run workflow**

Wait 2-3 minutes. Check your email and your dashboard at:
`https://YOUR-USERNAME.github.io/reddit-monitor/`

---

## Schedule

| Run | Schedule | Queries |
|-----|----------|---------|
| **Daily** | Mon–Fri 8 AM UTC | Brand + competitor mentions |
| **Weekly** | Monday 9 AM UTC | Full industry scan + comparisons |

Trigger runs manually anytime from the Actions tab.

---

## Run Locally

```bash
# Clone your fork
git clone https://github.com/YOUR-USERNAME/reddit-monitor.git
cd reddit-monitor

# Set your API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Run daily monitoring with AI analysis
python -m reddit_monitor monitor --daily --analyze

# Run weekly comprehensive scan
python -m reddit_monitor monitor --weekly --analyze

# One-shot deep scrape (baseline data collection)
python -m reddit_monitor scrape --analyze

# Re-analyze existing data with a different prompt/model
python -m reddit_monitor analyze
```

Requires Python 3.11+. No pip install needed — uses only stdlib.

---

## Configuration Reference

### `config.toml` sections

| Section | Required | Description |
|---------|----------|-------------|
| `[brand]` | Yes | `name` and `aliases` (lowercase variations, domains) |
| `[competitors]` | Yes | `names` — competitor names to track |
| `[subreddits]` | Yes | `high_value` — posts here are always relevant |
| `[keywords]` | Yes | `relevance` — filter terms; `geographic` — regional context |
| `[queries]` | Yes | `daily` and `weekly` search query definitions |
| `[analysis]` | No | `model` (default: claude-sonnet-4-20250514), `api_key`, `free_runs_per_month` |
| `[email]` | No | `subject_prefix` for email reports |
| `[settings]` | Yes | `user_agent`, `rate_delay`, `max_results_per_query`, etc. |

### AI Model Options

| Model | Cost/run | Best for |
|-------|----------|----------|
| `claude-sonnet-4-20250514` | ~$0.14 | Recommended — best value |
| `claude-haiku-4-5-20251001` | ~$0.04 | Budget — faster, less detailed |
| `claude-opus-4-6` | ~$0.54 | Premium — deepest analysis |

Change model in `config.toml`:
```toml
[analysis]
model = "claude-haiku-4-5-20251001"
```

---

## Project Structure

```
reddit-monitor/
├── reddit_monitor/       # Python package
│   ├── __main__.py       # CLI entry point
│   ├── api.py            # Reddit API (urllib, no deps)
│   ├── monitor.py        # Core monitoring logic
│   ├── analyze.py        # Claude AI analysis
│   ├── scrape.py         # One-shot deep scraper
│   ├── report.py         # Markdown report generation
│   ├── email_report.py   # Email delivery
│   ├── config.py         # TOML config loader
│   └── state.py          # State management
├── config.toml           # Your configuration
├── config.example.toml   # Example (Rise People)
├── docs/                 # GitHub Pages dashboard
├── data/                 # Generated reports & state (gitignored locally)
└── .github/workflows/    # GitHub Actions automation
```

---

## How It Works

1. **Search** — Runs configured queries against Reddit's public JSON API (`old.reddit.com/search.json`)
2. **Filter** — Keeps posts from target subreddits or matching keywords
3. **Prioritize** — URGENT (brand mention), HIGH (competitor), MEDIUM (industry)
4. **Enrich** — Fetches comments for top posts by engagement
5. **Analyze** — Sends everything to Claude for a 9-section strategic report
6. **Deliver** — Saves to `data/reports/`, copies to `docs/`, emails, commits

Zero external dependencies. Pure Python stdlib (urllib, json, smtplib).

---

## Want the hosted version?

Don't want to manage your own setup? Use the hosted version — just fill in 5 fields and get a report:

**[redditmonitor.jaskaranbedi.com](https://redditmonitor.jaskaranbedi.com)**

---

## License

MIT
