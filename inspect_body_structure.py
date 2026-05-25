import requests
from bs4 import BeautifulSoup

url = 'http://homeoint.org/books/boericmm/a/acon.htm'
r = requests.get(url, timeout=30)
r.encoding = r.apparent_encoding or 'latin-1'
soup = BeautifulSoup(r.text, 'lxml')

print('--- body direct children ---')
body = soup.body or soup
for idx, child in enumerate(body.children):
    if child.name:
        print(f"Child {idx}: <{child.name}> size: {len(str(child))}")
        text_preview = child.get_text(" ", strip=True)[:150]
        print(f"  Preview: {repr(text_preview)}")
