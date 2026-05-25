import requests
from bs4 import BeautifulSoup

url = 'http://homeoint.org/books/boericmm/a/acon.htm'
r = requests.get(url, timeout=30)
r.encoding = r.apparent_encoding or 'latin-1'
html_text = r.text

for parser in ['lxml', 'html.parser', 'html5lib']:
    try:
        soup = BeautifulSoup(html_text, parser)
        print(f"=== Parser: {parser} ===")
        body = soup.body or soup
        p_tags = body.find_all('p')
        print(f"Number of <p> tags in body: {len(p_tags)}")
        head_p = [p for p in p_tags if 'Head.--' in p.get_text()]
        if head_p:
            print(f"Found 'Head.--' <p> tag! Tag length: {len(str(head_p[0]))}")
            print(f"Text preview: {repr(head_p[0].get_text()[:200])}")
        else:
            print("Did not find 'Head.--' inside a <p> tag")
        print()
    except Exception as e:
        print(f"Parser {parser} failed: {e}\n")
