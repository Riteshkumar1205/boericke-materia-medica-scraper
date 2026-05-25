import requests

url = 'http://homeoint.org/books/boericmm/a/acon.htm'
r = requests.get(url, timeout=30)
r.encoding = r.apparent_encoding or 'latin-1'

html = r.text
idx = html.find('Head.--')
if idx != -1:
    print('--- RAW SOURCE AROUND Head.-- ---')
    print(html[idx-300:idx+800])
else:
    print('Head.-- not found in raw html')
