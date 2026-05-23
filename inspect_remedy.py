import requests
from bs4 import BeautifulSoup

url = 'http://homeoint.org/books/boericmm/a/abies-c.htm'
resp = requests.get(url, timeout=30)
resp.encoding = resp.apparent_encoding or 'latin-1'
soup = BeautifulSoup(resp.text, 'lxml')
print('title:', repr(soup.title.string if soup.title else ''))
print('--- b tags ---')
for b in soup.find_all('b')[:40]:
    txt = b.get_text().strip()
    if txt:
        print('B:', repr(txt))
print('--- sample sections ---')
for b in soup.find_all('b')[:20]:
    txt = b.get_text().strip()
    if not txt:
        continue
    print('B:', repr(txt))
    sib = b.next_sibling
    out = ''
    while sib and (hasattr(sib, 'name') and sib.name != 'b'):
        out += str(sib)
        sib = sib.next_sibling
    print('NEXT:', repr(out[:200]))
