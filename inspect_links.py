import requests
from bs4 import BeautifulSoup

url = 'http://homeoint.org/books/boericmm/a.htm'
resp = requests.get(url, timeout=30)
resp.encoding = resp.apparent_encoding or 'latin-1'
soup = BeautifulSoup(resp.text, 'lxml')

count = 0
for blockquote in soup.find_all('blockquote'):
    for a in blockquote.find_all('a', href=True):
        print(repr(a.get_text().strip()), '->', a['href'])
        count += 1
print('total', count)
