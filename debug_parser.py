import requests
from bs4 import BeautifulSoup
from utils.cleaner import clean_text
from utils.parser import (
    extract_title_and_common_name,
    _find_remedy_title_paragraph,
    parse_remedy_html,
)

url = 'http://homeoint.org/books/boericmm/a/abies-c.htm'
r = requests.get(url, timeout=30)
r.encoding = r.apparent_encoding or 'latin-1'
soup = BeautifulSoup(r.text, 'lxml')
full, common = extract_title_and_common_name(soup)
print('full', repr(full))
print('common', repr(common))
container = soup.find('blockquote') or soup.body or soup
paragraphs = container.find_all('p')
for i, p in enumerate(paragraphs):
    print(i, repr(clean_text(p.get_text(' '))))

title_paragraph = _find_remedy_title_paragraph(soup, full)
print('title paragraph found', title_paragraph is not None)
if title_paragraph is not None and title_paragraph in paragraphs:
    start = paragraphs.index(title_paragraph) + 1
    print('start index', start)
    for i, p in enumerate(paragraphs[start:], start=start):
        print('next', i, repr(clean_text(p.get_text(' '))))
else:
    print('title paragraph missing from paragraphs')

print('parse result:')
print(parse_remedy_html(soup, url, 'ABIES-C', 'A'))
