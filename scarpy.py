"""
Boericke's Homoeopathic Materia Medica — Production Web Scraper
================================================================

Scrapes:
    http://homeoint.org/books/boericmm/

Outputs:
    boericke_remedies.json

Features:
    - Full A–Z scraping
    - Resumable scraping
    - Robust error handling
    - Retry support
    - Failed URL logging
    - Progress tracking
    - Clean JSON schema
    - Optional MongoDB upload
    - Sample output generation

Usage:
    python scraper.py
    python scraper.py --upload
    python scraper.py --letters A,B,C
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
import unicodedata
from random import uniform
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from utils.validator import validate_remedies
from utils.parser import parse_remedy_html


# ============================================================
# Configuration
# ============================================================

BASE_URL = "http://homeoint.org/books/boericmm/"

OUTPUT_FILE = "boericke_remedies.json"
FAILED_FILE = "failed_urls.txt"
SAMPLE_OUTPUT_FILE = "sample_output.json"

SLEEP_MIN = 0.5
SLEEP_MAX = 1.0

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

log = logging.getLogger(__name__)

# ============================================================
# Utility Functions
# ============================================================


def normalize_text(text: Optional[str]) -> str:
    """Normalize whitespace, unicode, and punctuation."""
    if text is None:
        return ""

    value = str(text)
    value = unicodedata.normalize("NFC", value)
    value = value.replace("\u00A0", " ")
    value = value.replace("\u2013", "-")
    value = value.replace("\u2014", "-")
    value = value.replace("\u2018", "'")
    value = value.replace("\u2019", "'")
    value = value.replace("\u201C", '"')
    value = value.replace("\u201D", '"')
    value = re.sub(r"[\t\r\n]+", " ", value)
    value = re.sub(r"\s*([,;:.!?])\s*", r"\1 ", value)
    value = re.sub(r"\s*([()])\s*", r"\1", value)
    value = re.sub(r"\s{2,}", " ", value)
    value = value.strip(" \t\n\r-–—:;,.!?" + '"')
    value = re.sub(r"\s{2,}", " ", value)
    value = value.strip()
    return value


def is_noise_text(text: str) -> bool:
    """Detect page boilerplate, navigation, and metadata noise."""
    normalized = normalize_text(text)
    if not normalized:
        return False

    noise_patterns = [
        r"hom[oe]opathic materia medica",
        r"by william boericke",
        r"presented by",
        r"copyright",
        r"médi[- ]?t",
    ]

    return bool(re.search(r"(?:" + r"|".join(noise_patterns) + r")", normalized, re.IGNORECASE))


def clean_text(text: Optional[str]) -> str:
    """Clean text for structured output."""
    return normalize_text(text)


def _strip_boilerplate(text: str) -> str:
    """Remove known metadata and site boilerplate from a text value."""
    if not text:
        return ""

    cleaned = normalize_text(text)
    cleaned = re.sub(r"\b(?:hom[oe]opathic materia medica|by william boericke|presented by|copyright|médi[- ]?t|home|main|navigation|index)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" -–—:;,.!?" + '"')
    return normalize_text(cleaned)


def polite_sleep() -> None:
    """Sleep politely between requests."""
    time.sleep(uniform(SLEEP_MIN, SLEEP_MAX))


def log_failed(url: str, reason: str) -> None:
    """
    Log failed URLs.

    Args:
        url: Failed URL.
        reason: Failure reason.
    """
    with open(FAILED_FILE, "a", encoding="utf-8") as f:
        f.write(f"{url} # {reason}\n")

    log.error(f"✗ FAILED: {url} → {reason}")


# ============================================================
# Session + Retry
# ============================================================


def create_session() -> requests.Session:
    """
    Create requests session with retry support.

    Returns:
        Configured session.
    """
    session = requests.Session()

    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)

    session.mount("http://", adapter)
    session.mount("https://", adapter)

    session.headers.update(HEADERS)

    return session


# ============================================================
# Fetching Functions
# ============================================================


def fetch_letter_index(letter: str, session: requests.Session) -> str:
    """
    Fetch letter index page.

    Args:
        letter: A-Z letter.
        session: Active requests session.

    Returns:
        HTML content.
    """
    url = f"{BASE_URL}{letter.lower()}.htm"

    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()

        response.encoding = response.apparent_encoding or "latin-1"

        return response.text

    except requests.RequestException as exc:
        log_failed(url, str(exc))
        return ""


REMEDY_FILENAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\-]+\.htm$", re.IGNORECASE)
NAV_LABELS = {"MAIN", "HOME"}


def _is_valid_remedy_link(href: str, abbreviation: str) -> bool:
    if not href or not abbreviation:
        return False

    if abbreviation.upper() in NAV_LABELS:
        return False

    if len(abbreviation) <= 1:
        return False

    if not re.match(r"^[A-Za-z0-9\-]+$", abbreviation):
        return False

    if href.startswith("#") or href.lower().startswith("javascript:"):
        return False

    normalized = href.split("?")[0].split("#")[0]
    filename = normalized.rsplit("/", 1)[-1]

    if not filename.lower().endswith(".htm"):
        return False

    if filename.lower() in {"index.htm", "main.htm"}:
        return False

    if re.match(r"^[A-Za-z]\.htm$", filename.lower()):
        return False

    return bool(REMEDY_FILENAME_PATTERN.match(filename))


def _is_valid_remedy_url(url: str) -> bool:
    if not url:
        return False

    parsed = urlparse(url)
    path = parsed.path or ""
    filename = path.rsplit("/", 1)[-1].lower()

    if not filename.endswith(".htm"):
        return False

    if filename in {"index.htm", "main.htm"}:
        return False

    if re.match(r"^[a-z]\.htm$", filename):
        return False

    return bool(REMEDY_FILENAME_PATTERN.match(filename))


def parse_remedy_links(html: str, letter: str) -> list[dict]:
    """
    Extract remedy links from index page.

    Args:
        html: Letter page HTML.
        letter: Current letter.

    Returns:
        List of remedy metadata.
    """
    soup = BeautifulSoup(html, "lxml")

    remedies = []
    seen_urls = set()

    for blockquote in soup.find_all("blockquote"):
        for a_tag in blockquote.find_all("a", href=True):
            abbreviation = clean_text(a_tag.get_text()).upper()
            href = a_tag["href"].strip()

            if not _is_valid_remedy_link(href, abbreviation):
                continue

            full_url = href if href.startswith("http") else BASE_URL + href.lstrip("/")

            if full_url in seen_urls:
                continue

            seen_urls.add(full_url)
            remedies.append(
                {
                    "abbreviation": abbreviation,
                    "url": full_url,
                    "letter": letter,
                }
            )

    return remedies


# ============================================================
# Remedy Parsing
# ============================================================


def scrape_remedy_page(
    url: str,
    abbreviation: str,
    letter: str,
    session: requests.Session,
) -> Optional[dict]:
    """
    Scrape individual remedy page.

    Args:
        url: Remedy URL.
        abbreviation: Remedy abbreviation.
        letter: Letter category.
        session: Active session.

    Returns:
        Structured remedy dict.
    """
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()

        response.encoding = response.apparent_encoding or "latin-1"

        soup = BeautifulSoup(response.text, "lxml")

        return parse_remedy_html(
            soup=soup,
            url=url,
            abbreviation=abbreviation,
            letter=letter,
        )

    except requests.RequestException as exc:
        log_failed(url, str(exc))
        return None

    except Exception as exc:
        log_failed(url, f"Parsing Error: {exc}")
        return None




# ============================================================
# Save / Resume Helpers
# ============================================================


def load_existing_data() -> tuple[list[dict], set[str]]:
    """
    Load existing scraped data.

    Returns:
        Existing remedies + scraped URLs.
    """
    if not os.path.exists(OUTPUT_FILE):
        return [], set()

    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        valid_data = []
        urls = set()

        for item in data:
            source_url = item.get("source_url")
            if not isinstance(source_url, str):
                continue
            if not _is_valid_remedy_url(source_url):
                continue

            valid_data.append(item)
            urls.add(source_url)

        log.info(
            f"↩ Resuming previous scrape ({len(valid_data)} remedies)"
        )

        return valid_data, urls

    except Exception:
        return [], set()


def save_output(data: list[dict]) -> None:
    """
    Save JSON output.

    Args:
        data: Remedy list.
    """
    validation_issues = validate_remedies(data)
    if validation_issues:
        log.warning(
            f"⚠ Validation detected {len(validation_issues)} issue(s) in output"
        )
        for issue in validation_issues[:10]:
            log.warning(f"  - {issue}")
        if len(validation_issues) > 10:
            log.warning("  ...more issues suppressed")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # Save sample output
    with open(SAMPLE_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(
            data[:5],
            f,
            indent=2,
            ensure_ascii=False,
        )

    log.info(f"\n✔ Saved {len(data)} remedies")


# ============================================================
# MongoDB Upload (Optional Bonus)
# ============================================================


def upload_to_mongodb(data: list[dict]) -> None:
    """
    Upload remedies to MongoDB.

    Args:
        data: Remedy list.
    """
    try:
        from pymongo import MongoClient

    except ImportError:

        log.error(
            "pymongo not installed. Run: pip install pymongo"
        )

        sys.exit(1)

    client = MongoClient("mongodb://localhost:27017/")

    db = client["boericke"]

    collection = db["remedies"]

    inserted = 0
    updated = 0

    for remedy in data:

        result = collection.update_one(
            {"source_url": remedy["source_url"]},
            {"$set": remedy},
            upsert=True,
        )

        if result.upserted_id:
            inserted += 1
        else:
            updated += 1

    log.info(
        f"✔ MongoDB Upload Complete "
        f"({inserted} inserted, {updated} updated)"
    )

    client.close()


# ============================================================
# Main
# ============================================================


def main() -> None:
    """Main entry point."""

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload results to MongoDB",
    )

    parser.add_argument(
        "--letters",
        type=str,
        default="ALL",
        help="Comma separated letters. Example: A,B,C",
    )

    args = parser.parse_args()

    open(FAILED_FILE, "a", encoding="utf-8").close()

    all_remedies, scraped_urls = load_existing_data()

    session = create_session()

    if args.letters.upper() == "ALL":

        letters = [
            chr(ord("A") + i)
            for i in range(26)
        ]

    else:

        letters = [
            x.strip().upper()
            for x in args.letters.split(",")
        ]

    for letter in letters:

        log.info("\n" + "=" * 60)
        log.info(f"Letter: {letter}")
        log.info("=" * 60)

        html = fetch_letter_index(letter, session)

        polite_sleep()

        if not html:
            continue

        links = parse_remedy_links(html, letter)

        total = len(links)

        log.info(
            f"Found {total} remedies for letter {letter}"
        )

        current_count = 0

        for item in links:

            url = item["url"]

            abbreviation = item["abbreviation"]

            if url in scraped_urls:

                current_count += 1

                log.info(
                    f"→ Skipping existing: {abbreviation}"
                )

                continue

            remedy = scrape_remedy_page(
                url=url,
                abbreviation=abbreviation,
                letter=letter,
                session=session,
            )

            polite_sleep()

            if not remedy:
                continue

            all_remedies.append(remedy)

            scraped_urls.add(url)

            current_count += 1

            log.info(
                f"[{letter}] Scraped "
                f"{current_count}/{total} - "
                f"{remedy['full_name']}"
            )

        # Save checkpoint after each letter
        save_output(all_remedies)

    log.info("\n" + "=" * 60)
    log.info(
        f"COMPLETE — {len(all_remedies)} remedies scraped"
    )
    log.info("=" * 60)

    if args.upload:
        upload_to_mongodb(all_remedies)


if __name__ == "__main__":
    main()
