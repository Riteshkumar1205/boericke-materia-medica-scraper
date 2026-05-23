import requests
from bs4 import BeautifulSoup
from utils.cleaner import clean_text

url = 'http://homeoint.org/books/boericmm/a/abies-c.htm'
r = requests.get(url, timeout=30)
r.encoding = r.apparent_encoding or 'latin-1'
soup = BeautifulSoup(r.text, 'lxml')

body = soup.body or soup
paragraphs = body.find_all("p", recursive=False)

print(f"Total paragraphs: {len(paragraphs)}")
for i, p in enumerate(paragraphs):
    raw = p.get_text(" ")
    cleaned = clean_text(raw)
    print(f"\n[{i}] raw: {repr(raw[:100])}")
    print(f"    clean: {repr(cleaned[:100])}")
    if "--" in cleaned:
        print(f"    *** CONTAINS -- ***")
