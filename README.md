# Boericke's Homoeopathic Materia Medica Scraper

A production-grade, highly resilient web crawler and DOM-aware parsing pipeline designed to scrape and structure "William Boericke's Homoeopathic Materia Medica" from [homeoint.org](http://homeoint.org/books/boericmm/).

The scraper yields high-quality, validated, and normalized JSON structures of all ~688 remedies, completely eliminating section fragmentation and title/common-name bleed.

---

## Key Features

- **DOM-Aware Block Parser**: Operates recursively at the DOM element level rather than raw text lines. Mismatched tag scopes (such as interleaved legacy `<font>` and `<b>` tags) are automatically re-assembled into continuous semantic blocks.
- **Title and Common Name Isolation**: Intelligently separates full remedy names from common names (using dashes, parentheses, or case-transition boundaries) from the page's first content blocks.
- **Bleed Removal Pipeline**: Utilizes multi-pass prefix regex filters and formula/alias cleaning to ensure the `general` introduction has zero title/common-name bleed.
- **Title Case Normalization**: Standardizes raw section keys into clean Title Case (e.g. `"MIND"` -> `"Mind"`, `"HEAD"` -> `"Head"`), while preserving medical punctuation.
- **Resume Support**: Gracefully tracks state, allowing the crawler to resume from its last completed letter checkpoint without redundant web requests.
- **Encoding Hardening**: Forces and prioritizes Windows-1252 (CP1252) decoding to natively support character ligatures (like U+0152 `Œ` in `HOMŒOPATHIC`) without causing control character corruption or site-header filtering failures.
- **Resilient Retry & Polite Scraping**: Embeds an HTTP retry strategy (backoff factor with status code filters) and polite randomized sleep bounds to respect host server traffic rates.
- **Comprehensive Quality Validator**: Incorporates a strict data-quality engine checking for required fields, malformed section keys, metadata leakage, text truncation, duplicate URLs, and schema anomalies.

---

## Project Structure

```text
Jarvi/
│
├── utils/
│   ├── __init__.py      # Package initialization
│   ├── fetcher.py       # Resilient HTTP fetching and CP1252 decoding
│   ├── parser.py        # DOM-aware block parsing and bleed cleaning
│   ├── cleaner.py       # Basic text cleaning & normalization utilities
│   ├── saver.py         # JSON serialization and checkpoint loading
│   └── validator.py     # Rigorous quality assurance validator
│
├── scraper.py           # Production modular scraping entry point
├── scarpy.py            # Deduplicated monolithic command-line entry point
├── requirements.txt     # Explicitly pinned library dependencies
└── README.md            # Project overview & documentation
```

---

## Installation & Setup

1. **Prerequisites**: Ensure Python 3.8+ is installed on your system.
2. **Virtual Environment**: Create and activate a clean virtual environment:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```
3. **Install Dependencies**: Install the pinned production requirements:
   ```bash
   pip install -r requirements.txt
   ```

---

## Usage

### Run Modular Scraper
To run the production-grade modular scraper:
```bash
# Scrape all remedies (A to Z)
python -X utf8 scraper.py --letters ALL

# Scrape specific letter categories
python -X utf8 scraper.py --letters A,B,C
```

### Run Command Entry Point
To run the command-line utility (deduplicated to share the modular engine, including optional MongoDB uploads):
```bash
# Run scrape
python -X utf8 scarpy.py --letters ALL

# Run scrape and upload results to a local MongoDB instance
python -X utf8 scarpy.py --letters ALL --upload
```

*(Note: The `-X utf8` flag forces Python to utilize UTF-8 encoding for standard I/O stream communication, preventing encoding crash issues on default Windows terminals.)*

---

## Output Schema

The scraper saves all scraped remedies in `boericke_remedies.json` with a subset sample of the first 5 records in `sample_output.json`. 

Each remedy strictly adheres to the following structural schema:
```json
{
  "abbreviation": "ACON",
  "full_name": "ACONITUM NAPELLUS",
  "common_name": "Monkshood",
  "source_url": "http://homeoint.org/books/boericmm/a/acon.htm",
  "letter": "A",
  "general": "A state of fear, anxiety; anguish of mind and body. Physical and mental restlessness...",
  "sections": {
    "Mind": "Great fear, anxiety , and worry accompany every ailment, however trivial...",
    "Head": "Fullness; heavy , pulsating, hot, bursting , burning undulating sensation...",
    "Eyes": "Red, inflamed. Feel dry and hot , as if sand in them..."
  },
  "relationships": "Acids, wine and coffee, lemonade, and acid fruits modify its action..."
}
```

---

## Error Handling & Resiliency

- **Failed URL Logging**: Any network timeouts, HTTP errors (4xx/5xx), or document parse exceptions are logged in `failed_urls.txt` along with their exact error reason, ensuring transparency.
- **Checkpoint Saves**: Results are committed to the file system after each completed letter category. If a scrape is interrupted, relaunching the scraper will skip already processed URLs.

---

## Data Validation Strategy

The validation subsystem (`utils/validator.py`) inspects every record against strict rules:
1. **Schema Check**: Confirms all standard keys are present, matching types, and non-empty.
2. **Key Normalization Check**: Ensures section keys are valid canonical headings and not long-tail fragments.
3. **No Title Bleed**: Heuristically checks the `general` text to verify it does not contain the remedy title or common name.
4. **No HTML/Control Characters**: Verifies the text contains no remnant tags, raw control chars, or unresolved unicode replacement points.
5. **No Text Truncation**: Heuristically checks the end of sections to confirm they do not terminate mid-sentence.

---

## Assumptions & Limitations

- **Source HTML Consistency**: Assumes the target layout strictly follows the standard Boericke index format on homeoint.org (where indexes reside under relative letters `/a/`, `/b/`, etc., and remedy detail pages are structured under relative paths).
- **Network Traffic Rules**: Imposes a 0.5–1.0s randomized request delay to adhere to respectful crawl practices. Scraping all ~688 records sequentially takes roughly 8–12 minutes.
