import requests
from bs4 import BeautifulSoup

url = 'http://homeoint.org/books/boericmm/a/abies-c.htm'
resp = requests.get(url, timeout=30)
resp.encoding = resp.apparent_encoding or 'latin-1'
soup = BeautifulSoup(resp.text, 'lxml')

print('title:', repr(soup.title.string if soup.title else ''))
print('body length:', len(str(soup.body) if soup.body else ''))

count = 0
for b in soup.find_all('b'):
    text = b.get_text().strip()
    if not text:
        continue
    count += 1
    if count <= 150:
        print(count, repr(text))
print('total bold tags with text:', count)
