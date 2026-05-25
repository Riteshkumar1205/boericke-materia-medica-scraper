import requests
from bs4 import BeautifulSoup
import re
from typing import List, Tuple, Optional

urls = [
    ('ACON', 'http://homeoint.org/books/boericmm/a/acon.htm'),
    ('ABIES-C', 'http://homeoint.org/books/boericmm/a/abies-c.htm'),
    ('ACETAN', 'http://homeoint.org/books/boericmm/a/acetan.htm'),
    ('ABR', 'http://homeoint.org/books/boericmm/a/abr.htm'),
    ('ABROT', 'http://homeoint.org/books/boericmm/a/abrot.htm'),
]

def clean_text(value: Optional[str]) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def get_dom_text_blocks(soup_element) -> List[str]:
    blocks = []
    current_block = []

    def flush_block():
        if current_block:
            text = " ".join(current_block)
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                blocks.append(text)
            current_block.clear()

    def traverse(node):
        if node.name in {"script", "style", "title"}:
            return
        is_block = node.name in {
            "p", "div", "blockquote", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "table"
        }
        if is_block:
            flush_block()

        for child in node.children:
            if isinstance(child, str):
                val = child.replace("\r", " ").replace("\n", " ")
                if val.strip():
                    current_block.append(val)
            else:
                traverse(child)

        if is_block:
            flush_block()

    traverse(soup_element)
    flush_block()
    return blocks

def is_site_header(text: str) -> bool:
    normalized = text.strip().upper()
    if normalized in {"HOME", "MAIN", "INDEX", "NEXT", "PREVIOUS", "|"}:
        return True
    
    headers = [
        r"hom[oe]opathic materia medica",
        r"by william boericke",
        r"presented by",
        r"copyright",
    ]
    return any(re.search(pat, text, re.IGNORECASE) for pat in headers)

def sanitize_full_name(name: str) -> str:
    if ":" in name:
        left, right = name.split(":", 1)
        if "=" in right or ";" in right:
            name = left
    return clean_text(name)

def parse_title_block(text: str, abbreviation: str) -> Tuple[str, Optional[str]]:
    text = clean_text(text)
    
    # Remove any leading "Home" if it's there
    text = re.sub(r"^home\s+", "", text, flags=re.IGNORECASE)

    # Check for parentheses, e.g. "GLONOINUM (Nitro-glycerine)"
    if "(" in text and ")" in text:
        inner = re.search(r"\(([^)]+)\)", text)
        if inner:
            common = clean_text(inner.group(1))
            full = clean_text(re.sub(r"\s*\([^)]*\)", "", text))
            return sanitize_full_name(full), common

    # Check for dashes, e.g. "ABIES CANADENSIS - PINUS CANADENSIS - Hemlock Spruce"
    dashes = [r"\s*--+\s*", r"\s+-\s+"]
    for dash in dashes:
        parts = re.split(dash, text)
        if len(parts) >= 2:
            # Check if there are multiple parts (like full - variant - common)
            # We take the first part as full, and combine the rest as common
            full = parts[0]
            common = " - ".join(parts[1:])
            return sanitize_full_name(full), clean_text(common)

    # Split by case difference
    tokens = text.split()
    full_tokens = []
    for token in tokens:
        token_clean = re.sub(r"[^A-Za-z0-9\-]", "", token)
        if token_clean.isupper() and len(token_clean) > 1:
            full_tokens.append(token)
        else:
            break
            
    if full_tokens:
        full = " ".join(full_tokens)
        common = " ".join(tokens[len(full_tokens):])
        return sanitize_full_name(full), (clean_text(common) if common else None)

    return sanitize_full_name(text), None

for abbr, url in urls:
    r = requests.get(url, timeout=30)
    r.encoding = r.apparent_encoding or 'latin-1'
    soup = BeautifulSoup(r.text, 'lxml')
    
    blocks = get_dom_text_blocks(soup.body or soup)
    filtered = [b for b in blocks if not is_site_header(b)]
    
    print(f"=== Remedy: {abbr} ===")
    if filtered:
        title_b = filtered[0]
        fn, cn = parse_title_block(title_b, abbr)
        print(f"Raw Title Block: {repr(title_b)}")
        print(f"Parsed Full Name: {repr(fn)}")
        print(f"Parsed Common Name: {repr(cn)}")
        print(f"First block of content: {repr(filtered[1][:120])}")
    else:
        print("No blocks found!")
    print()
