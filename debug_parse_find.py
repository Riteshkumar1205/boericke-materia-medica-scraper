import requests
from bs4 import BeautifulSoup

url = 'http://homeoint.org/books/boericmm/a/abies-c.htm'
r = requests.get(url, timeout=30)
r.encoding = r.apparent_encoding or 'latin-1'
soup = BeautifulSoup(r.text, 'lxml')
container = soup.find('blockquote') or soup.body or soup
paragraphs = container.find_all('p')
print('container type', container.name)
print('paragraph count', len(paragraphs))
for i, p in enumerate(paragraphs):
    print('---', i, '---')
    print('repr', repr(p.get_text(' ')))
    print('children', [(c.name if hasattr(c, 'name') else 'str', repr(str(c)[:80])) for c in p.contents])
