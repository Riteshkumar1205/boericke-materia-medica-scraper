import argparse
import logging
import os
import sys
import time
from random import uniform
from string import ascii_uppercase
from typing import List, Set

from utils.cleaner import clean_text
from utils.fetcher import create_session, fetch_html
from utils.parser import extract_remedy_links, parse_remedy_html
from utils.saver import append_failed_url, load_existing_data, save_output

BASE_URL = "http://homeoint.org/books/boericmm/"
OUTPUT_FILE = "boericke_remedies.json"
FAILED_FILE = "failed_urls.txt"
SAMPLE_OUTPUT_FILE = "sample_output.json"
SLEEP_MIN = 0.5
SLEEP_MAX = 1.0

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def polite_sleep() -> None:
    time.sleep(uniform(SLEEP_MIN, SLEEP_MAX))


def normalize_letters(value: str) -> List[str]:
    if value.strip().upper() == "ALL":
        return list(ascii_uppercase)

    letters = []
    for candidate in map(str.strip, value.split(",")):
        candidate = candidate.upper()
        if len(candidate) == 1 and candidate in ascii_uppercase:
            letters.append(candidate)
    return sorted(dict.fromkeys(letters))


def log_failed(url: str, reason: str) -> None:
    append_failed_url(FAILED_FILE, url, reason)
    logger.error(f"✗ FAILED: {url} → {reason}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Production-grade scraper for Boericke remedies."
    )
    parser.add_argument(
        "--letters",
        type=str,
        default="ALL",
        help="Comma-separated letters or ALL. Example: A,B,C",
    )

    args = parser.parse_args()

    os.makedirs(os.path.dirname(FAILED_FILE) or ".", exist_ok=True)
    open(FAILED_FILE, "a", encoding="utf-8").close()

    existing_data, scraped_urls = load_existing_data(OUTPUT_FILE)
    if existing_data:
        logger.info(
            f"↩ Resuming previous scrape ({len(existing_data)} remedies)"
        )

    session = create_session()
    letters = normalize_letters(args.letters)

    if not letters:
        logger.error("No valid letters specified. Use --letters A,B,C or --letters ALL.")
        sys.exit(1)

    results = existing_data.copy()

    for letter in letters:
        logger.info("\n" + "=" * 60)
        logger.info(f"Letter: {letter}")
        logger.info("=" * 60)

        index_url = f"{BASE_URL}{letter.lower()}.htm"
        try:
            index_html = fetch_html(index_url, session)
        except Exception as exc:
            log_failed(index_url, str(exc))
            continue

        polite_sleep()

        remedies = extract_remedy_links(index_html, BASE_URL, letter)
        logger.info(f"Index URL: {index_url}")
        logger.info(f"Index HTML length: {len(index_html)}")
        logger.info(f"Found {len(remedies)} remedies for letter {letter}")

        for item in remedies:
            url = item["url"]
            abbreviation = item["abbreviation"]

            if url in scraped_urls:
                logger.info(f"→ Skipping existing: {abbreviation}")
                continue

            try:
                remedy_html = fetch_html(url, session)
            except Exception as exc:
                log_failed(url, str(exc))
                polite_sleep()
                continue

            try:
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(remedy_html, "lxml")
                remedy = parse_remedy_html(
                    soup=soup,
                    url=url,
                    abbreviation=abbreviation,
                    letter=letter,
                )
            except Exception as exc:
                log_failed(url, f"Parsing Error: {exc}")
                polite_sleep()
                continue

            if remedy["source_url"] in scraped_urls:
                continue

            results.append(remedy)
            scraped_urls.add(url)
            logger.info(
                f"[{letter}] Scraped {len(scraped_urls)} - {remedy['full_name']}"
            )
            polite_sleep()

        save_output(OUTPUT_FILE, SAMPLE_OUTPUT_FILE, results)

    logger.info("\n" + "=" * 60)
    logger.info(f"COMPLETE — {len(results)} remedies scraped")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
