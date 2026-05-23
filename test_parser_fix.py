#!/usr/bin/env python
"""Quick test of the improved parser on a specific remedy."""

import json
import requests
from bs4 import BeautifulSoup
from utils.parser import parse_remedy_html
from utils.validator import validate_remedy

# Test on ACON remedy
TEST_URL = "http://homeoint.org/books/boericmm/a/acon.htm"
ABBREVIATION = "ACON"
LETTER = "A"

print("=" * 70)
print(f"Testing parser on: {ABBREVIATION}")
print("=" * 70)

# Fetch the page
try:
    response = requests.get(TEST_URL, timeout=10)
    response.raise_for_status()
    html = response.text
except Exception as e:
    print(f"ERROR fetching URL: {e}")
    exit(1)

# Parse with BeautifulSoup
soup = BeautifulSoup(html, "lxml")

# Parse using improved parser
remedy = parse_remedy_html(soup, TEST_URL, ABBREVIATION, LETTER)

# Display results
print("\nPARSED REMEDY:")
print("-" * 70)
print(json.dumps(remedy, indent=2, ensure_ascii=False))

# Validate
print("\n" + "=" * 70)
print("VALIDATION RESULTS:")
print("=" * 70)
seen_urls = set()
errors = validate_remedy(remedy, seen_urls)
if errors:
    for error in errors:
        print(f"  ✗ {error}")
else:
    print("  ✓ All validations passed!")

# Summary
print("\n" + "=" * 70)
print("SUMMARY:")
print("=" * 70)
print(f"Full Name:    {remedy.get('full_name')}")
print(f"Common Name:  {remedy.get('common_name')}")
print(f"Sections:     {len(remedy.get('sections', {}))} found")
if remedy.get('sections'):
    print(f"  - {', '.join(remedy.get('sections', {}).keys())}")
print(f"Relationships: {'Present' if remedy.get('relationships') else 'None'}")
print(f"General text:  {len(remedy.get('general', ''))} chars")
