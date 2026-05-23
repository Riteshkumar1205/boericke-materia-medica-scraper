#!/usr/bin/env python
"""Quick test of section parsing on ACON remedy."""

import requests
from bs4 import BeautifulSoup
from utils.parser import parse_remedy_html

TEST_URL = "http://homeoint.org/books/boericmm/a/acon.htm"
ABBREVIATION = "ACON"
LETTER = "A"

# Fetch and parse
response = requests.get(TEST_URL, timeout=10)
soup = BeautifulSoup(response.text, "lxml")
remedy = parse_remedy_html(soup, TEST_URL, ABBREVIATION, LETTER)

# Show parsed result
print("=" * 70)
print("PARSED ACON REMEDY:")
print("=" * 70)
print(f"\nFull Name: {remedy['full_name']}")
print(f"Common Name: {remedy['common_name']}")
print(f"\n# Sections Found: {len(remedy['sections'])}")

if remedy['sections']:
    print("\nSection Names:")
    for i, section_name in enumerate(remedy['sections'].keys(), 1):
        content = remedy['sections'][section_name]
        content_preview = content[:80] + "..." if len(content) > 80 else content
        print(f"  {i}. {section_name}: {content_preview}")
else:
    print("  (NO SECTIONS FOUND)")

print(f"\nRelationships: {'Present' if remedy['relationships'] else 'None'}")
if remedy['relationships']:
    rel_preview = remedy['relationships'][:100] + "..." if len(remedy['relationships']) > 100 else remedy['relationships']
    print(f"  {rel_preview}")

print(f"\nGeneral Text Length: {len(remedy['general'])} chars")
print(f"General Text: {remedy['general'][:150]}...")
