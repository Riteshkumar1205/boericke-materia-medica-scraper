#!/usr/bin/env python
"""Debug section parsing to see what headings are detected."""

import requests
from bs4 import BeautifulSoup
import re
from utils.parser import parse_remedy_html, _split_text_into_lines, _extract_all_text_content, extract_title_and_common_name
from utils.cleaner import clean_text, is_footer_marker, is_site_header

TEST_URL = "http://homeoint.org/books/boericmm/a/acon.htm"
ABBREVIATION = "ACON"
LETTER = "A"

# Fetch and parse
response = requests.get(TEST_URL, timeout=10)
soup = BeautifulSoup(response.text, "lxml")

# Extract text like the parser does
full_name, common_name = extract_title_and_common_name(soup, ABBREVIATION)
text_content = _extract_all_text_content(soup)

# Remove site headers
text_content = re.sub(
    r"^.*?presented by\s+médi\s*[-]?\s*t\s+",
    "",
    text_content,
    flags=re.IGNORECASE | re.DOTALL,
)
text_content = re.sub(r"^\s*home\s+", "", text_content, flags=re.IGNORECASE)

# Find footer
footer_match = re.search(
    r'\s+Copyright\s*©|Copyright\s+©.*?Médi\s*[-]?\s*T|^(Copyright|Dose).*?$',
    text_content,
    re.IGNORECASE | re.MULTILINE,
)
if footer_match:
    text_content = text_content[: footer_match.start()]

# Split lines
lines = _split_text_into_lines(text_content)

# Check which lines match the heading pattern
print("=" * 70)
print("LINES THAT MATCH HEADING PATTERN:")
print("=" * 70)

heading_pattern = r'^([A-Z][A-Za-z0-9\s\-\&/()\']*?)\s*(?:\.[-]{1,}|[-]{1,}\.?|\.{2,}[-]*)\s*(.*)$'

count = 0
for i, line in enumerate(lines[:50]):  # First 50 lines
    match = re.match(heading_pattern, line, re.IGNORECASE)
    if match:
        heading, content = match.groups()
        print(f"\nLine {i}: MATCH")
        print(f"  Heading: '{heading}'")
        print(f"  Content: '{content[:80]}'...")
        count += 1

print(f"\n\nTotal heading matches in first 50 lines: {count}")
print("\nFull text length:", len(text_content))
print("Total lines:", len(lines))
