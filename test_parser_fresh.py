import requests
from bs4 import BeautifulSoup
from utils.parser import parse_remedy_html

urls = [
    ('ABIES-C', 'http://homeoint.org/books/boericmm/a/abies-c.htm'),
    ('ACON', 'http://homeoint.org/books/boericmm/a/acon.htm'),
]

for abbr, url in urls:
    r = requests.get(url, timeout=30)
    r.encoding = r.apparent_encoding or 'latin-1'
    soup = BeautifulSoup(r.text, 'lxml')
    result = parse_remedy_html(soup, url, abbr, 'A')
    print(f"{abbr}: {len(result['general'])} chars of general")
    print(f"  Sections: {list(result['sections'].keys())}")
    print(f"  Relationships: {result['relationships'][:50] if result['relationships'] else None}")
    print()
