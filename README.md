# Boericke Materia Medica Scraper

Production-grade scraper for the Boericke Homoeopathic Materia Medica site:

- Source: `http://homeoint.org/books/boericmm/`
- Output: `boericke_remedies.json`
- Sample output: `sample_output.json`
- Failed URL log: `failed_urls.txt`

## Features

- Crawls A–Z index pages
- Filters only valid remedy links
- Parses remedy pages into a clean structured schema
- Removes duplicate remedies deterministically
- Extracts `relationships` outside of `sections`
- Normalizes general text and section content
- Supports resumable scraping
- Writes an automatic `sample_output.json`

## Requirements

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run a full scrape:

```bash
python scraper.py --letters ALL
```

Run a limited scrape for one or more letters:

```bash
python scraper.py --letters A,B,C
```

## Output schema

Each remedy record includes:

- `abbreviation`
- `full_name`
- `common_name`
- `source_url`
- `letter`
- `general`
- `sections`
- `relationships`
