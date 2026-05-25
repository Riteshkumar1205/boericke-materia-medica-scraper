import requests
from bs4 import BeautifulSoup
import re
from typing import List, Tuple, Optional, Dict

urls = [
    ('ACON', 'http://homeoint.org/books/boericmm/a/acon.htm'),
    ('ABIES-C', 'http://homeoint.org/books/boericmm/a/abies-c.htm'),
    ('ACETAN', 'http://homeoint.org/books/boericmm/a/acetan.htm'),
    ('ABR', 'http://homeoint.org/books/boericmm/a/abr.htm'),
    ('ABROT', 'http://homeoint.org/books/boericmm/a/abrot.htm'),
]

CANONICAL_SECTION_ALIASES: Dict[str, str] = {
    "MIND": "Mind",
    "HEAD": "Head",
    "EYES": "Eyes",
    "EARS": "Ears",
    "NOSE": "Nose",
    "FACE": "Face",
    "MOUTH": "Mouth",
    "THROAT": "Throat",
    "STOMACH": "Stomach",
    "ABDOMEN": "Abdomen",
    "RECTUM": "Rectum",
    "STOOL": "Stool",
    "URINE": "Urine",
    "URINARY": "Urinary",
    "MALE": "Male",
    "FEMALE": "Female",
    "RESPIRATORY": "Respiratory",
    "CHEST": "Chest",
    "HEART": "Heart",
    "BACK": "Back",
    "EXTREMITIES": "Extremities",
    "LIMBS": "Limbs",
    "SKIN": "Skin",
    "FEVER": "Fever",
    "SLEEP": "Sleep",
    "MODALITIES": "Modalities",
    "DOSE": "Dose",
    "CLINICAL": "Clinical",
    "GENERALITIES": "Generalities",
    "DREAMS": "Dreams",
    "DESIRES": "Desires",
    "AVERSIONS": "Aversions",

    "EYE": "Eyes",
    "EAR": "Ears",
    "STOOLS": "Stool",
    "DOSES": "Dose",
    "MODALITY": "Modalities",

    "RELATIONSHIPS": "Relationships",
    "RELATIONSHIP": "Relationships",
    "RELATIONS": "Relationships",
    "RELATION": "Relationships",
    "COMPARE": "Compare",
    "COMPLEMENTARY": "Complementary",
    "ANTIDOTE": "Antidote",
    "ANTIDOTES": "Antidotes",
    "INIMICAL": "Inimical",
    "INCOMPATIBLE": "Incompatible",
    "FOLLOWS": "Follows",
    "FOLLOWED": "Followed",
    "SIMILAR": "Similar",
    "COMPATIBLE": "Compatible",
    "COLLATERAL": "Collateral",
}

RELATIONSHIP_HEADING_SET = {
    "Relationships", "Compare", "Complementary", "Antidote", "Antidotes",
    "Inimical", "Incompatible", "Follows", "Followed", "Similar", "Compatible", "Collateral"
}

INLINE_HEADING_RE = re.compile(
    r"^\s*(?P<name>[A-Za-z][A-Za-z\s\-&]{1,30})\s*(?:\.?:?)\s*--+\s*(?P<rest>.*)$"
)

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
        r"hom[oœŒe]{1,2}pathic materia medica",
        r"by william boericke",
        r"presented by",
        r"copyright",
    ]
    return any(re.search(pat, text, re.IGNORECASE) for pat in headers)

def _normalize_section_heading(raw_heading: str) -> Optional[str]:
    heading = clean_text(raw_heading).strip().upper()
    heading = heading.rstrip(":;,-.")
    return CANONICAL_SECTION_ALIASES.get(heading)

def detect_section_heading(block: str) -> Tuple[Optional[str], Optional[str]]:
    block_clean = clean_text(block).upper().rstrip(".:- ")
    if block_clean in CANONICAL_SECTION_ALIASES:
        return CANONICAL_SECTION_ALIASES[block_clean], None
        
    match = INLINE_HEADING_RE.match(block)
    if match:
        name = match.group("name")
        rest = match.group("rest")
        canon_name = _normalize_section_heading(name)
        if canon_name:
            return canon_name, clean_text(rest)
            
    if ":" in block:
        left, right = block.split(":", 1)
        canon_left = _normalize_section_heading(left)
        if canon_left:
            return canon_left, clean_text(right)
            
    return None, None

def sanitize_full_name(name: str) -> str:
    if ":" in name:
        left, right = name.split(":", 1)
        if "=" in right or ";" in right:
            name = left
    return clean_text(name)

def parse_title_block(text: str, abbreviation: str) -> Tuple[str, Optional[str]]:
    text = clean_text(text)
    text = re.sub(r"^home\s+", "", text, flags=re.IGNORECASE)

    if "(" in text and ")" in text:
        inner = re.search(r"\(([^)]+)\)", text)
        if inner:
            common = clean_text(inner.group(1))
            full = clean_text(re.sub(r"\s*\([^)]*\)", "", text))
            return sanitize_full_name(full), common

    dashes = [r"\s*--+\s*", r"\s+-\s+"]
    for dash in dashes:
        parts = re.split(dash, text)
        if len(parts) >= 2:
            full = parts[0]
            common = " - ".join(parts[1:])
            return sanitize_full_name(full), clean_text(common)

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

def strip_title_bleed(general: str, full_name: str, common_name: Optional[str]) -> str:
    value = clean_text(general)
    if not value:
        return ""

    fn = clean_text(full_name)
    cn = clean_text(common_name) if common_name else ""

    def strip_prefix(v: str, prefix: str) -> str:
        if not prefix:
            return v
        pattern = r"^\s*" + re.escape(prefix) + r"(?:\s*[-,:;.]?\s*)"
        return re.sub(pattern, "", v, flags=re.IGNORECASE).strip()

    for _ in range(3):
        before = value
        if fn and cn:
            value = strip_prefix(value, f"{fn} {cn}")
            value = strip_prefix(value, f"{fn} ({cn})")
            value = strip_prefix(value, f"{fn} - {cn}")
        if fn:
            value = strip_prefix(value, fn)
        if cn:
            value = strip_prefix(value, cn)
        value = value.lstrip(" -:;,.\"'")
        if value == before:
            break

    # Strip formula prefixes
    value = re.sub(r"^(?:[A-Z]{1,4}\s*=\s*[^;]{1,80};\s*){1,8}", "", value).strip()
    value = re.sub(r"^[A-Z]{1,4}\s*=\s*[A-Za-z]{2,}\s*", "", value).strip()

    return clean_text(value)

def parse_remedy_html(soup: BeautifulSoup, url: str, abbreviation: str, letter: str) -> dict:
    blocks = get_dom_text_blocks(soup.body or soup)
    filtered = [b for b in blocks if not is_site_header(b)]
    
    # Extract title and common name
    full_name, common_name, intro_start = parse_names_and_intro(filtered, abbreviation)
    
    general_parts = []
    sections = {}
    current_section = None
    current_content = []
    relationships_parts = []
    
    def flush_section():
        nonlocal current_section, current_content, sections, relationships_parts
        if current_section:
            content = clean_text(" ".join(current_content))
            if content:
                if current_section in RELATIONSHIP_HEADING_SET:
                    relationships_parts.append(content)
                else:
                    sections[current_section] = content
        current_section = None
        current_content = []

    # Loop through content blocks starting after Title and Common Name
    for block in filtered[intro_start:]:
        # Cutoff at copyright / footer markers
        if re.search(r"copyright\s*©|copyright\s*Š\s*Médi-T|presented by", block, re.IGNORECASE):
            break
            
        heading, rest = detect_section_heading(block)
        if heading:
            flush_section()
            current_section = heading
            if rest:
                current_content.append(rest)
        else:
            if current_section:
                current_content.append(block)
            else:
                general_parts.append(block)
                
    flush_section()
    
    general = clean_text(" ".join(general_parts))
    general = strip_title_bleed(general, full_name, common_name)
    
    relationships = clean_text(" ".join(relationships_parts)) if relationships_parts else None
    
    return {
        "abbreviation": abbreviation,
        "full_name": full_name,
        "common_name": common_name,
        "source_url": url,
        "letter": letter,
        "general": general,
        "sections": sections,
        "relationships": relationships,
    }

def parse_names_and_intro(filtered_blocks: List[str], abbreviation: str) -> Tuple[str, Optional[str], int]:
    if not filtered_blocks:
        return abbreviation, None, 0

    first_block = filtered_blocks[0]
    full_name, common_name = parse_title_block(first_block, abbreviation)
    
    intro_start_idx = 1
    if not common_name and len(filtered_blocks) > 1:
        second_block = filtered_blocks[1]
        is_heading, _ = detect_section_heading(second_block)
        if not is_heading and len(second_block) < 60:
            common_name = clean_text(second_block)
            intro_start_idx = 2
            
    return full_name, common_name, intro_start_idx

for abbr, url in urls:
    r = requests.get(url, timeout=30)
    # Decode as windows-1252 (cp1252) specifically to parse Œ correctly
    r.encoding = "windows-1252"
    soup = BeautifulSoup(r.text, 'lxml')
    result = parse_remedy_html(soup, url, abbr, 'A')
    
    print(f"=== Parser Test: {abbr} ===")
    print(f"Full Name:   {result['full_name']}")
    print(f"Common Name: {result['common_name']}")
    print(f"General:     {result['general'][:100]}...")
    print(f"Sections ({len(result['sections'])}): {list(result['sections'].keys())}")
    print(f"Relationships: {result['relationships']}")
    print()
