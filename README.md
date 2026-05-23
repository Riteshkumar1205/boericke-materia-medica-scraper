# Boericke's Materia Medica Scraper

A production-grade Python scraper that extracts all remedy data from [Boericke's Homoeopathic Materia Medica](http://homeoint.org/books/boericmm/index.htm) and outputs a clean, structured JSON dataset.

Built as a data engineering assignment for **jarvis.care** — an AI-powered clinical assistant for homeopathic practitioners.

---


## Project Structure

```
boericke-materia-medica-scraper/
├── scraper.py                  # Main entry point
├── requirements.txt            # Dependencies
├── boericke_remedies.json      # Full dataset (688 remedies)
├── sample_output.json          # 5-remedy sample
├── failed_urls.txt             # Failed URLs log (empty)
└── utils/
    ├── fetcher.py              # HTTP session with retry support
    ├── parser.py               # HTML parsing — links and remedy pages
    ├── cleaner.py              # Text cleaning and normalisation
    ├── saver.py                # JSON output and resume logic
    └── validator.py            # Schema validation
```

---

## Setup

**Requirements:** Python 3.9+

```bash
# Clone the repo
git clone https://github.com/Riteshkumar1205/boericke-materia-medica-scraper.git
cd boericke-materia-medica-scraper

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux

# Install dependencies
pip install -r requirements.txt
```

---

## Usage

### Scrape all letters (A–Z)

```bash
python scraper.py
```

### Scrape specific letters only

```bash
python scraper.py --letters A,B,C
```

### Resume an interrupted run

Just run the same command again. The scraper checks `boericke_remedies.json` on startup, loads all previously scraped URLs, and skips them automatically. No duplicates, no re-fetching.

```
↩ Resuming previous scrape (101 remedies)
```

---

## How It Works

### 1. Letter index parsing
Each letter's index page (e.g., `a.htm`) lists remedies as anchor tags inside a `<blockquote>`. The scraper extracts abbreviations and page URLs from these.

### 2. Remedy page parsing
Each individual remedy page contains:
- A **general description** — opening paragraphs before any section heading
- **Organ-system sections** — separated by bold headings formatted as `Head.--`, `Stomach.--`, etc.
- An optional **Relationships** block

Section headings across the site are inconsistent — some pages use `Head.--`, others `HEAD--`, others omit punctuation entirely. The parser uses a defensive regex pattern that handles all variants found across the full A–Z dataset.

### 3. Rate limiting
A random 0.5–1.0 second delay between requests avoids overloading the server.

### 4. Error handling
Network errors and parsing failures are caught, logged to `failed_urls.txt`, and skipped. The scrape continues uninterrupted.

### 5. Retry logic
The HTTP session is configured with automatic retries (3 attempts, exponential backoff) on 429, 500, 502, 503, and 504 responses.

---

## Output Schema

Each remedy in `boericke_remedies.json` follows this structure:

```json
{
  "abbreviation": "ACON",
  "full_name": "ACONITUM NAPELLUS",
  "common_name": "Monkshood",
  "source_url": "http://homeoint.org/books/boericmm/a/acon.htm",
  "letter": "A",
  "general": "A state of fear, anxiety, anguish of mind and body...",
  "sections": {
    "Mind": "Great fear, anxiety, and worry accompany every ailment...",
    "Head": "Fullness, heavy, pulsating, hot, bursting headache...",
    "Fever": "Cold stage most marked; cold sweat; ice-cold fingertips...",
    "Dose": "Third to thirtieth potency."
  },
  "relationships": "Compare: Coff, Cham, Bell. Complementary: Sulph, Calc, Sep."
}
```

| Field | Required | Notes |
|---|---|---|
| `abbreviation` | Yes | Uppercase, from index anchor text |
| `full_name` | Yes | Full Latin name from the page heading |
| `common_name` | No | `null` if not present on the page |
| `source_url` | Yes | Full URL of the remedy page |
| `letter` | Yes | Single uppercase letter A–Z |
| `general` | Yes | Opening text before the first section heading |
| `sections` | Yes | Dict of section name → section text. `{}` if none. |
| `relationships` | No | Cross-reference text, or `null` if absent |

**Text cleaning:** all HTML tags stripped, whitespace collapsed to single spaces, original punctuation preserved.

---

## Sample Progress Output

```
↩ Resuming previous scrape (101 remedies)

============================================================
Letter: B
============================================================
Index URL: http://homeoint.org/books/boericmm/b.htm
Index HTML length: 6943
Found 30 remedies for letter B
[B] Scraped 102 - BACILLINUM BURNETT
[B] Scraped 103 - BADIAGA
[B] Scraped 104 - BALSAMUM PERUVIANUM
...
[B] Scraped 131 - BUTYRICUM ACIDUM

============================================================
COMPLETE — 688 remedies scraped
============================================================
```

---

## Dependencies

```
requests
beautifulsoup4
lxml
```

Install with:

```bash
pip install -r requirements.txt
```

---

## Notes

- The scraper targets a public, freely accessible reference text. All requests are rate-limited and polite.
- `failed_urls.txt` is created automatically on first run. If empty after completion, all pages were fetched successfully.
- The `--letters` flag is useful for testing. Run `--letters A` first to validate the parser before scraping A–Z.

---
