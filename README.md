# Ekşi Sözlük Harvester

A Playwright-based scraper that collects all entries under a given Ekşi Sözlük topic and saves them to a UTF-8 JSON file.

- **Headless Chromium** (default)
- **Robust pagination** via `rel=next` (follows pages until the end)
- **Optional cookie injection** (for logged-in / restricted views)
- **Clean JSON output** (no favorites field)
- **Minimal, readable code**

## Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
- [Output Format](#output-format)
- [Options](#options)
- [Tips & Troubleshooting](#tips--troubleshooting)
- [Automation (Windows Task Scheduler)](#automation-windows-task-scheduler)
- [Security & Ethics](#security--ethics)
- [Project Structure](#project-structure)
- [License](#license)

## Features

✅ Headless scraping (no visible browser window by default)  
✅ Next-page following via `rel="next"` until no more pages remain  
✅ Optional cookies (`--cookie` flag or `EKSI_COOKIE` env var)  
✅ Progress logs (page count & new entries per page)  
✅ UTF-8 JSON output with stable fields  

## Quick Start

```bash
# 0) Create & activate a virtual environment (recommended)
python -m venv venv

# Windows PowerShell
venv\Scripts\Activate.ps1

# macOS/Linux
# source venv/bin/activate

# 1) Install dependencies
pip install playwright beautifulsoup4
python -m playwright install chromium

# 2) Run (headless by default)
python eksi_play_harvester.py "https://eksisozluk.com/mckinsey--266991" -o out.json
```

## Installation

### Prerequisites

- Python 3.9+
- pip
- (Windows) PowerShell execution policy may need:
  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  ```

### Dependencies

- **Playwright** (Chromium)
- **BeautifulSoup4**

Install:

```bash
pip install playwright beautifulsoup4
python -m playwright install chromium
```

> Playwright downloads a bundled Chromium build used by the scraper.

## Usage

### Basic

```bash
python eksi_play_harvester.py "<TOPIC_SLUG_OR_URL>" -o entries.json

# Example with full URL:
python eksi_play_harvester.py "https://eksisozluk.com/mckinsey--266991" -o out.json

# Example with slug:
python eksi_play_harvester.py "mckinsey--266991" -o out.json
```

### Visible Browser (for debugging)

```bash
python eksi_play_harvester.py "<TOPIC>" -o out.json --no-headless
```

### Limit Pages / Adjust Delay

```bash
# Visit only first 3 pages
python eksi_play_harvester.py "<TOPIC>" -o out.json --max-pages 3

# Wait 2.0 seconds between page navigations (default: 1200 ms)
python eksi_play_harvester.py "<TOPIC>" -o out.json --delay 2000
```

### Optional: Cookies (for logged-in or restricted content)

> **Warning:** Never commit cookies to your repo.

```bash
# Pass cookies directly
python eksi_play_harvester.py "<TOPIC>" -o out.json --cookie "cf_clearance=...; __cf_bm=...; _ga=...; _gid=..."

# Or use an environment variable (recommended)
# Windows PowerShell:
$env:EKSI_COOKIE = 'cf_clearance=...; __cf_bm=...; _ga=...'
python eksi_play_harvester.py "<TOPIC>" -o out.json

# (After use)
Remove-Item Env:\EKSI_COOKIE
```

> Cookie value is the single-line Cookie header copied from your browser's DevTools → Network tab → Request Headers.

## Output Format

Each entry is stored as a JSON object with the following fields:

```json
{
  "entry_id": "123456789",
  "author": "author_nick",
  "author_url": "https://eksisozluk.com/biri/author_nick",
  "date": "20.09.2025 22:41",
  "permalink": "https://eksisozluk.com/entry/123456789",
  "content": "Full entry text here..."
}
```

The file is a JSON array (UTF-8, pretty-printed).

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `topic` | — | Topic slug or full URL. First page is normalized as `?p=1`. |
| `-o, --output` | `entries.json` | Output JSON filename. |
| `--max-pages` | `None` | Upper bound on visited pages (stops earlier if no next page). |
| `--delay` | `1200` | Delay (milliseconds) between page navigations. |
| `--cookie` | `None` | Optional single-line Cookie header. Alternatively set `EKSI_COOKIE` env var. |
| `--no-headless` | headless on | Show the browser (useful for debugging). |

## Tips & Troubleshooting

- **Too slow / rate limits**: decrease `--delay` cautiously (e.g., 800–1200 ms). Too aggressive values can trigger protections.

- **Empty results**: run with `--no-headless` to visually confirm DOM content; some pages take longer → try a higher `--delay`.

- **Login-required content**: supply a valid cookie (see above). Cookies expire—refresh from browser if needed.

- **Duplicates**: entries are de-duplicated by `entry_id`.

- **Progress feedback**: the script prints page number, raw entries discovered, and new entries appended.

## Automation (Windows Task Scheduler)

1. Open **Task Scheduler** → **Create Basic Task…**

2. **Trigger**: e.g., Daily at 09:00.

3. **Action**: Start a Program
   - **Program/script**: `python`
   - **Add arguments**:
     ```
     C:\path\to\eksi_play_harvester.py "https://eksisozluk.com/<slug>--<id>" -o C:\path\to\out.json
     ```
   - **Start in**: `C:\path\to\your\venv\Scripts` (or ensure your PATH uses the venv's python)

4. (Optional) Set `EKSI_COOKIE` as a system/user environment variable if needed.

> On Linux/macOS, use `cron` with your venv's Python.

## Security & Ethics

- **Respect robots/ToS**. Use reasonable delays, don't overload the site.
- **Keep cookies private**. Do not commit them or share them.
- **Research & educational use** recommended. You are responsible for compliant usage.

Add a `.gitignore` to avoid committing artifacts:

```gitignore
# Python
__pycache__/
*.pyc
venv/

# Outputs
out.json
*.json

# Local env/cookies
.env
```

## Project Structure

```
Eksi-Sozluk-Harvester/
├─ eksi_play_harvester.py    # main script
├─ venv/                     # virtual environment (not committed)
├─ README.md
└─ (outputs) out.json        # example output (ignored)
```

This tool is for educational and research purposes only. Please respect Ekşi Sözlük’s Terms of Service and do not use it for abusive or commercial scraping.
