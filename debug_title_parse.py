import requests
from bs4 import BeautifulSoup
from scarpy import extract_title_and_common_name, BASE_URL

urls = [
    BASE_URL + 'a/abies-c.htm',
    BASE_URL + 'a/acon.htm',
    BASE_URL + 'a/arn.htm',
]
for url in urls:
    r = requests.get(url, timeout=30)
    r.encoding = r.apparent_encoding or 'latin-1'
    soup = BeautifulSoup(r.text, 'lxml')
    print('URL:', url)
    print('Title tag text:', soup.title.string if soup.title else None)
    print('First 10 b tags:')
    for i,b in enumerate(soup.find_all('b')[:10]):
        print(i, repr(b.get_text(' ')))
    print('extract title:', extract_title_and_common_name(soup))
    print('-----')
