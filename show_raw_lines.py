#!/usr/bin/env python
"""Show actual lines around detected headings."""

import requests
from bs4 import BeautifulSoup
import re
from utils.parser import _split_text_into_lines, _extract_all_text_content, extract_title_and_common_name

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

# Show first 30 lines to see context
print("=" * 70)
print("FIRST 30 LINES OF PARSED TEXT:")
print("=" * 70)

for i, line in enumerate(lines[:30]):
    marker = " <-- HEADING PATTERN MATCH" if re.match(r'^([A-Z][A-Za-z0-9\s\-\&/()\']*?)\s*(?:\.[-]{1,}|[-]{1,}\.?|\.{2,}[-]*)\s*(.*)$', line, re.IGNORECASE) else ""
    print(f"{i:3d}: {line[:80]}{marker}")
