import requests
from bs4 import BeautifulSoup
from utils.parser import parse_remedy_html
import json

url = 'http://homeoint.org/books/boericmm/a/acon.htm'
r = requests.get(url, timeout=30)
r.encoding = r.apparent_encoding or 'latin-1'
soup = BeautifulSoup(r.text, 'lxml')
result = parse_remedy_html(soup, url, 'ACON', 'A')

print("Full result for ACON:")
print(json.dumps(result, indent=2, ensure_ascii=False)[:3000])
