# WebsiteBrief

An extensible, agentic pipeline for scraping structured data from websites and generating AI-powered Markdown briefs via the Claude API. Designed to run weekly — either interactively or on a schedule.

---

## Architecture

```
run.py
  ├─ BaseScraper (scrapers/base.py)
  │   └─ D2LScraper (scrapers/d2l.py)  ←  scrapes your LMS
  │
  ├─ 7-day filter (core/date_utils.py) ←  strips stale assignments
  │
  ├─ BaseLLMClient (core/base_llm_client.py)
  │   └─ ClaudeClient (core/claude_client.py)  ←  generates the brief
  │
  └─ storage (core/storage.py)          ←  saves brief + conversation log
```

Every scraper outputs the same `WeeklyCourseData` schema. The AI client only knows about that schema, so swapping scrapers or AI providers never requires touching the pipeline logic.

---

## Prerequisites

- Python 3.10 or newer ([python.org](https://www.python.org/downloads/))
- Git
- An [Anthropic API key](https://console.anthropic.com/)

---

## Quick Start (Windows)

**1. Clone the repo and open a PowerShell terminal in the project folder.**

**2. Run the one-time setup script:**

```powershell
powershell -ExecutionPolicy Bypass -File setup.ps1
```

This script:
- Sets the PowerShell execution policy
- Creates a `.venv` virtual environment
- Installs all Python dependencies
- Downloads the Playwright Chromium browser
- Creates `outputs/` directories
- Copies `.env.example` → `.env`
- Installs a pre-commit hook that blocks accidental API key commits

**3. Fill in your secrets:**

Open `.env` and add your Anthropic API key and D2L username:

```
ANTHROPIC_API_KEY=sk-ant-...
D2L_USERNAME=your_username_here
```

**4. Configure your D2L URL:**

Open `config.yaml` and set your institution's D2L login URL:

```yaml
scrapers:
  d2l:
    login_url: "https://learn.myuniversity.edu/d2l/login"
```

**5. Activate the virtual environment** (required every time you open a new terminal):

```powershell
.\.venv\Scripts\Activate.ps1
```

**6. Run:**

```powershell
python run.py
```

A browser window will open. Complete your login and MFA, then press Enter in the terminal. The brief will appear in `outputs/briefs/`.

---

## Calibrating D2L Selectors

D2L institutions customize their Brightspace theme, so the default CSS selectors in `config.yaml` may not match yours. To fix this:

1. Open your D2L in Chrome and log in.
2. Press **F12** → **Elements** tab.
3. Find the course links in the nav or home page.
4. Right-click → **Copy** → **Copy selector**.
5. Paste it into `config.yaml` under `scrapers.d2l.selectors.course_links`.
6. Repeat for the assignments table and announcement widget.

No Python changes are needed — all selectors live in `config.yaml`.

---

## CLI Reference

| Flag | Description |
|---|---|
| *(no flags)* | Full interactive run |
| `--dry-run` | Scrape only; print the AI prompt without calling the API |
| `--unattended` | Exit cleanly if the scraper requires human login (for scheduled runs) |
| `--scraper NAME` | Override the active scraper in config.yaml |
| `--verbose` | Enable DEBUG log level |
| `--no-save` | Skip writing output files (useful for testing) |
| `--no-cleanup` | Skip deletion of old brief files this run |
| `--help` | Show all options |

---

## Output Files

| Location | Contents |
|---|---|
| `outputs/briefs/brief_YYYYMMDD_HHMMSS.md` | Generated weekly brief |
| `outputs/conversations/conversation_*.json` | Full prompt + response (for debugging) |
| `outputs/logs/websitebrief.log` | Rotating log file (DEBUG level, 5 MB max) |

Brief files older than `brief_retention_days` (default: 30 days) are deleted automatically on each run.

---

## Adding a New Scraper

Say you want to scrape GitHub trending repos:

1. Create `scrapers/github_trending.py`:

```python
from scrapers.base import BaseScraper
from core.models import WeeklyCourseData

class GitHubTrendingScraper(BaseScraper):
    requires_auth = False      # no login needed

    def scrape(self) -> list[WeeklyCourseData]:
        # use playwright or requests here
        ...

    def close(self) -> None:
        ...
```

2. Add a config block in `config.yaml`:

```yaml
scrapers:
  active: github_trending
  github_trending:
    url: "https://github.com/trending"
    language: python
```

3. Add one `elif` branch in `run.py`'s `build_scraper()`:

```python
elif active == "github_trending":
    from scrapers.github_trending import GitHubTrendingScraper
    return GitHubTrendingScraper(scraper_cfg)
```

That is all. The rest of the pipeline (AI client, storage, logging) requires zero changes.

---

## Adding a New AI Provider

1. Create `core/openai_client.py` and subclass `BaseLLMClient`.
2. Add a `providers.openai:` block to `config.yaml`.
3. Add one `elif` branch in `run.py`'s `build_llm_client()`.
4. Add your `OPENAI_API_KEY` to `.env`.

---

## Running Tests

```powershell
pytest tests/ -v
```

Tests cover: data models, abstract base classes, date parsing, storage I/O, and cleanup logic.
