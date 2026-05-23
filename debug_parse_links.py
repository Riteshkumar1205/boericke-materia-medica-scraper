import requests
from scarpy import parse_remedy_links, BASE_URL

html = requests.get(BASE_URL + 'a.htm', timeout=30).text
links = parse_remedy_links(html, 'A')
print('links', len(links))
print('unique urls', len({l['url'] for l in links}))
print('sample count', min(20, len(links)))
for item in links[:20]:
    print(item)
