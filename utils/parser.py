import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

from .cleaner import clean_text, normalize_abbreviation, is_footer_marker, is_site_header

BAD_LINK_LABELS = {"MAIN", "HOME"}
REMEDY_FILENAME_PATTERN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9\-]+\.htm$', re.IGNORECASE)

# Patterns for section headings: "Head.--", "Head.-", "Head --", "HEAD.--", "Sleep.--", etc.
SECTION_HEADING_PATTERN = re.compile(
    r'^\s*(?P<heading>[A-Z][A-Za-z0-9\s\-\&/()\']+?)\s*(?:\.\s*[-]{1,}|[-]{1,}\s*\.?|\.[-]{1,})\s*$|'
    r'^\s*(?P<heading2>[A-Z][A-Za-z0-9\s\-\&/()\']+?)\s*(?:\.\s*[-]{1,}|[-]{1,}\s*\.?|\.[-]{1,})\s+(?P<content>.+)$',
    re.IGNORECASE,
)

# Common section names in Boericke's Materia Medica
KNOWN_SECTIONS = {
    "MIND", "HEAD", "FACE", "MOUTH", "THROAT", "EYES", "EARS", "NOSE",
    "STOMACH", "ABDOMEN", "RECTUM", "STOOL", "URINE", "URINARY",
    "MALE", "FEMALE", "RESPIRATORY", "CHEST", "HEART", "BACK",
    "EXTREMITIES", "LIMBS", "SKIN", "FEVER", "SLEEP", "MODALITIES",
    "DOSE", "RELATIONSHIPS", "RELATIONSHIP", "COMPARE", "ANTIDOTE",
}


def canonicalize_url(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse(parsed._replace(query="", fragment=""))


def _is_valid_remedy_url(href: str, base_url: str) -> bool:
    if not href:
        return False

    if href.startswith("#") or href.lower().startswith("javascript:"):
        return False

    absolute = urljoin(base_url, href.strip())
    parsed = urlparse(absolute)
    path = parsed.path or ""

    if not path.lower().endswith(".htm"):
        return False

    filename = path.rsplit("/", 1)[-1]
    if filename.lower() in {"index.htm", "main.htm"}:
        return False

    if re.match(r'^[A-Za-z]\.htm$', filename):
        return False

    return bool(REMEDY_FILENAME_PATTERN.match(filename))


def _normalize_href(href: str, base_url: str) -> str:
    return canonicalize_url(urljoin(base_url, href.strip()))


def extract_remedy_links(html: str, base_url: str, letter: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    blockquotes = soup.find_all("blockquote")

    remedies: List[Dict[str, str]] = []
    seen_urls = set()

    for blockquote in blockquotes:
        for a_tag in blockquote.find_all("a", href=True):
            if not _is_valid_remedy_url(a_tag["href"], base_url):
                continue

            abbreviation = normalize_abbreviation(a_tag.get_text())
            if not abbreviation or abbreviation in BAD_LINK_LABELS or len(abbreviation) == 1:
                continue

            url = _normalize_href(a_tag["href"], base_url)
            if url in seen_urls:
                continue

            seen_urls.add(url)
            remedies.append(
                {
                    "abbreviation": abbreviation,
                    "url": url,
                    "letter": letter,
                }
            )

    return remedies


def _extract_title_from_bold_tags(soup: BeautifulSoup) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract remedy title and common name from <b> tags.
    Expected format: "<b>REMEDY NAME\nCommon Name</b>" or "<b>REMEDY NAME Common Name</b>"
    """
    for b_tag in soup.find_all("b"):
        text = b_tag.get_text()
        if not text or not text.strip():
            continue

        # Skip if it's the site header
        if re.search(r"homoeopathic|materia medica|by william|presented by", text, re.IGNORECASE):
            continue

        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if not lines:
            continue

        first_line = clean_text(lines[0])

        # Check if first line looks like a remedy name (contains uppercase or Latin names)
        if not first_line or len(first_line) < 3:
            continue

        # Extract common name if it's on a second line
        common_name = None
        if len(lines) > 1:
            second_line = clean_text(lines[1])
            # Second line is common name if it doesn't look like a section heading
            if second_line and not re.match(r'^[A-Z\-]+$', second_line):
                if len(second_line) > 2 and second_line not in {"A", "B", "C"}:
                    common_name = second_line

        return first_line, common_name

    return None, None


def _extract_title_from_text_content(soup: BeautifulSoup) -> Tuple[Optional[str], Optional[str]]:
    """
    Fallback: Extract title from page text content.
    Look for patterns like "REMEDY NAME Common Name" at the start of content.
    """
    body = soup.body or soup
    text_content = body.get_text(" ", strip=True)

    # Remove site headers
    text_content = re.sub(
        r"home\s+homoeopathic materia medica.*?presented by\s+médi\s*[-]?\s*t\s+",
        "",
        text_content,
        flags=re.IGNORECASE | re.DOTALL,
    )

    lines = text_content.split("\n")
    for line in lines[:5]:  # Check first few lines
        line = clean_text(line)
        if not line or len(line) < 5:
            continue

        # Pattern: "UPPERCASE_NAME lowercase_common_name"
        parts = line.split(maxsplit=2)
        if len(parts) >= 1:
            first_word = parts[0]
            # Check if it looks like a remedy name
            if re.match(r'^[A-Z][A-Za-z\-]*$', first_word) and len(first_word) > 2:
                full_name = first_word
                if len(parts) > 1:
                    second_word = parts[1]
                    # If second word is not all caps, it's likely the common name
                    if not second_word.isupper() or len(parts) > 2:
                        # Combine all remaining words as full name
                        full_name = " ".join(parts[:2]) if len(parts) == 2 else parts[0]
                        common_name = " ".join(parts[1:]) if len(parts) > 1 and not parts[1].isupper() else None
                        if common_name:
                            return full_name, common_name
                return full_name, None

    return None, None


def extract_title_and_common_name(soup: BeautifulSoup, abbreviation: str) -> Tuple[str, Optional[str]]:
    """
    Extract remedy title and common name with fallbacks.
    """
    # Try bold tag extraction first
    full_name, common_name = _extract_title_from_bold_tags(soup)
    if full_name:
        return full_name, common_name

    # Try page title tag
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        title_text = clean_text(title_tag.string)
        # Extract remedy name from page title: "REMEDY NAME - HOMOEOPATHIC..."
        match = re.match(r'^([A-Z][A-Za-z0-9\s\-]*?)\s*(?:-|–)\s*HOM', title_text, re.IGNORECASE)
        if match:
            full_name = match.group(1).strip()
            if full_name:
                return full_name, None

    # Try text content extraction
    full_name, common_name = _extract_title_from_text_content(soup)
    if full_name:
        return full_name, common_name

    # Fallback: use abbreviation
    return abbreviation, None


def _detect_section_heading(line: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Detect section headings that may be embedded in a line.
    
    Examples:
    - "some content. Head.-- Content" -> ("HEAD", "Content")
    - "text) Mind.-- Great fear" -> ("MIND", "Great fear")  
    - Standalone: "Head.-- " -> ("HEAD", "")
    
    Headings typically appear after:
    - Period + space: ". Mind.--"
    - Closing paren + space: ") Eyes.--"
    - Start of line: "Mind.--"
    
    Returns:
        (heading_name, remaining_content_after_heading) or (None, None)
    """
    line = line.strip()
    if not line:
        return None, None

    # Pattern to find headings - either at start of line or after punctuation
    # Matches: [optional preceding punctuation and space] HEADING-PATTERN [optional content]
    # Pattern structure:
    # (?:^|[.)\]]\\s+)  - Start of line OR period/paren/bracket + space
    # ([A-Z][A-Za-z0-9\s\-\&/()\']*?)  - Heading words
    # \s*(?:\.[-]{1,}|[-]{1,}\.?|\.{2,}[-]*)  - Delimiter pattern
    # \s*(.*)$  - Optional content
    
    match = re.search(
        r'(?:^|[.)\]]\s+)([A-Z][A-Za-z0-9\s\-\&/()\']*?)\s*(?:\.[-]{1,}|[-]{1,}\.?|\.{2,}[-]*)\s*(.*)$',
        line,
        re.IGNORECASE,
    )
    
    if not match:
        return None, None
    
    heading = match.group(1).strip().upper()
    content = match.group(2).strip() if match.group(2) else None
    
    # Known remedy body section headings (comprehensive list)
    # These cover the standard homeopathic materia medica sections
    KNOWN_SECTIONS = {
        'MIND', 'HEAD', 'EYES', 'EYE', 'EARS', 'EAR', 'NOSE', 'FACE', 'MOUTH', 'TEETH',
        'THROAT', 'STOMACH', 'ABDOMEN', 'RECTUM', 'STOOL', 'URINE', 'MALE', 'FEMALE',
        'RESPIRATORY', 'CHEST', 'HEART', 'BACK', 'SPINE', 'EXTREMITIES', 'LIMBS',
        'HANDS', 'FEET', 'HIP', 'KNEE', 'SHOULDER', 'SLEEP', 'DREAMS', 'SKIN', 'FEVER',
        'MODALITIES', 'DESIRES', 'AVERSIONS', 'CONSTITUTION', 'GENERALITIES',
        'CLINICAL', 'RELATIONS', 'RELATIONSHIP', 'DOSES', 'ANTIDOTES',
        'COMPARE', 'COMPLEMENTARY', 'FOLLOWS', 'FOLLOWED', 'SIMILAR', 'INCOMPATIBLE',
        'AGGRAVATION', 'AMELIORATION', 'WORSE', 'BETTER', 'PULSE', 'CIRCULATION',
        'PERSPIRATION', 'HAIR', 'MUCOUS MEMBRANES', 'GLANDS', 'BONES', 'JOINTS',
        'MUSCLES', 'NERVES', 'BLOOD', 'SEXUAL', 'LACTATION', 'PREGNANCY',
    }
    
    # Validation checks
    heading_words = heading.split()
    
    # Check if heading is in known sections (first word match)
    first_word = heading_words[0] if heading_words else ""
    
    # Accept if first word is in known sections list
    if first_word in KNOWN_SECTIONS:
        return heading, content
    
    # Reject if too long or multi-word (likely a related remedy)
    # Known sections are typically 1-3 words max
    if len(heading_words) > 3:
        return None, None
    
    # Additional validation for unknown sections
    # Must be at least 3 chars, no single letters
    if len(heading) < 3:
        return None, None
    
    # Reject known false positives
    problematic = {'GASTRO', 'STOMACH', 'TOBACCO', 'ACONITE', 'ACON'}
    if heading in problematic and content and content[0].islower():
        return None, None
    
    # For unknown sections, accept if it looks reasonable
    # (already passed most filters)
    return heading, content


def _split_text_into_lines(text: str) -> List[str]:
    """Split text into semantic lines, handling various line break patterns."""
    # Normalize line breaks
    text = re.sub(r'\r\n|\r', '\n', text)
    lines = text.split('\n')
    # Clean and filter empty lines
    lines = [clean_text(line) for line in lines if clean_text(line)]
    return lines


def _extract_all_text_content(soup: BeautifulSoup) -> str:
    """Extract all text content from the page body, excluding navigation."""
    body = soup.body or soup
    # Remove script and style tags
    for tag in body(['script', 'style']):
        tag.decompose()

    # Get all text
    text = body.get_text(" ", strip=True)
    return text


def parse_remedy_html(
    soup: BeautifulSoup,
    url: str,
    abbreviation: str,
    letter: str,
) -> Dict[str, object]:
    """
    Parse remedy page HTML into structured data using semantic text parsing.
    
    Strategy:
    1. Extract title and common name from bold tags
    2. Get all text content
    3. Remove site headers and metadata
    4. Split into semantic lines
    5. Parse sections by detecting heading patterns
    6. Stop at footer markers
    7. Extract relationships separately
    """

    # Step 1: Extract title
    full_name, common_name = extract_title_and_common_name(soup, abbreviation)

    # Step 2: Get all text content
    text_content = _extract_all_text_content(soup)

    # Step 3: Remove site headers
    text_content = re.sub(
        r"^.*?presented by\s+médi\s*[-]?\s*t\s+",
        "",
        text_content,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Remove leading "Home" navigation
    text_content = re.sub(r"^\s*home\s+", "", text_content, flags=re.IGNORECASE)

    # Step 4: Find footer cutoff point
    footer_match = re.search(
        r'\s+Copyright\s*©|Copyright\s+©.*?Médi\s*[-]?\s*T|^(Copyright|Dose).*?$',
        text_content,
        re.IGNORECASE | re.MULTILINE,
    )
    if footer_match:
        text_content = text_content[: footer_match.start()]

    # Step 5: Split into lines
    lines = _split_text_into_lines(text_content)

    # Step 6: Parse sections and general text
    general_parts: List[str] = []
    sections: Dict[str, str] = {}
    current_section: Optional[str] = None
    current_content: List[str] = []
    relationships: Optional[str] = None
    first_section_found = False

    for line in lines:
        # Check if this is a section heading
        heading, inline_content = _detect_section_heading(line)

        if heading:
            first_section_found = True
            
            # Save previous section if open
            if current_section is not None:
                section_content = clean_text(" ".join(current_content))
                if section_content:
                    if "RELATIONSHIP" in current_section:
                        relationships = section_content
                    else:
                        sections[current_section] = section_content
                current_content = []

            # Start new section
            current_section = heading
            # Add inline content if present
            if inline_content:
                current_content.append(inline_content)
            continue

        # Accumulate content
        if current_section is not None:
            current_content.append(line)
        else:
            # This is part of general introduction (before first section)
            if line and not is_site_header(line):
                general_parts.append(line)

    # Close final section
    if current_section is not None:
        section_content = clean_text(" ".join(current_content))
        if section_content:
            if "RELATIONSHIP" in current_section:
                relationships = section_content
            else:
                sections[current_section] = section_content

    # Build general text: title + intro (only content before first section)
    general_lines = []

    # Add title and common name as intro context
    if full_name:
        title_intro = full_name
        if common_name:
            title_intro += f" {common_name}"
        general_lines.append(title_intro)

    # Add general content (skip if it's just repeating title)
    for part in general_parts:
        if part and full_name not in part:
            general_lines.append(part)

    general = clean_text(" ".join(general_lines))

    # Ensure we don't have footer pollution
    if general and is_footer_marker(general[-100:]):
        # Remove footer from the end
        general = re.sub(r'\s*Copyright.*?$', '', general, flags=re.IGNORECASE | re.DOTALL)
        general = clean_text(general)

    # Normalize relationships format
    if relationships:
        relationships = clean_text(relationships)

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

