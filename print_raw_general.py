import requests

url = 'http://homeoint.org/books/boericmm/a/acon.htm'
r = requests.get(url, timeout=30)
r.encoding = r.apparent_encoding or 'latin-1'

html = r.text
idx = html.find('A state of fear')
if idx != -1:
    print('--- RAW GENERAL PARAGRAPH ---')
    print(html[idx-100:idx+600])
