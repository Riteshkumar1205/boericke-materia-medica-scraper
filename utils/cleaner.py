import re
import unicodedata
from typing import Optional


def clean_text(value: Optional[str]) -> str:
    """Normalize whitespace and trim text."""
    if value is None:
        return ""

    text = str(value)
    # Normalize unicode
    text = unicodedata.normalize("NFC", text)
    # Remove excessive whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_abbreviation(value: str) -> str:
    """Normalize remedy abbreviation text."""
    return clean_text(value).upper()


def is_footer_marker(text: str) -> bool:
    """Check if text contains footer/metadata markers."""
    markers = [
        r"copyright\s*©",
        r"médi\s*[-]?\s*t\s*\d{4}",
        r"homoeopathic materia medica",
        r"by william boericke",
        r"presented by",
    ]
    for marker in markers:
        if re.search(marker, text, re.IGNORECASE):
            return True
    return False


def is_site_header(text: str) -> bool:
    """Check if text is site header/navigation."""
    headers = [
        r"^home\s*$",
        r"^main\s*$",
        r"^index\s*$",
        r"navigation",
        r"homoeopathic materia medica",
        r"by william boericke",
    ]
    for header in headers:
        if re.search(header, text, re.IGNORECASE):
            return True
    return False
