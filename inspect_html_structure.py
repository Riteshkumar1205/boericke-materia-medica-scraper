#!/usr/bin/env python
"""Examine the raw HTML structure."""

import requests
from bs4 import BeautifulSoup

TEST_URL = "http://homeoint.org/books/boericmm/a/acon.htm"

# Fetch
response = requests.get(TEST_URL, timeout=10)
soup = BeautifulSoup(response.text, "lxml")

# Find body
body = soup.body or soup

# Show first 50 lines of body text content
text = body.get_text()
lines = text.split('\n')

print("=" * 70)
print("RAW HTML TEXT CONTENT (first 50 lines):")
print("=" * 70)

for i, line in enumerate(lines[:50]):
    if line.strip():
        print(f"{i:3d}: {line[:100]}")
