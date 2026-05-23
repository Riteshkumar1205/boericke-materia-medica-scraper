import requests
from utils.parser import extract_remedy_links

BASE_URL = 'http://homeoint.org/books/boericmm/'
url = BASE_URL + 'a.htm'
resp = requests.get(url, timeout=30)
resp.encoding = resp.apparent_encoding or 'latin-1'
links = extract_remedy_links(resp.text, BASE_URL, 'A')
print(len(links))
for link in links[:20]:
    print(link)
