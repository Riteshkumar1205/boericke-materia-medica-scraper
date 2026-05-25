import requests
from bs4 import BeautifulSoup

url = 'http://homeoint.org/books/boericmm/a/acon.htm'
r = requests.get(url, timeout=30)
r.encoding = r.apparent_encoding or 'latin-1'
soup = BeautifulSoup(r.text, 'lxml')

body = soup.body or soup
children = list(body.children)

print('--- RAW HTML CHUNKS ---')
for idx in range(5, 25):
    if idx < len(children):
        child = children[idx]
        if child.name:
            print(f"Child {idx}: <{child.name}>")
            print(str(child))
            print("="*40)
