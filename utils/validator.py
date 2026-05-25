import re
import unicodedata
from typing import Any, Dict, List, Optional, Set

ABBREVIATION_PATTERN = re.compile(r"^[A-Z0-9\-]{2,}$")
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")

# Comprehensive metadata/footer markers
FOOTER_MARKERS = [
    r"copyright\s*©",
    r"médi\s*[-]?\s*t\s*\d{4}",
    r"homoeopathic materia medica",
    r"by william boericke",
    r"presented by",
    r"^home\s*$",
    r"^main\s*$",
    r"^index\s*$",
    r"^\s*\|",  # Navigation pipes
]

SITE_METADATA_PATTERN = re.compile(
    "|".join(FOOTER_MARKERS),
    re.IGNORECASE,
)

CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F-\x9F]")
EXCESSIVE_SPACES_PATTERN = re.compile(r"\s{2,}")
MALFORMED_UNICODE_PATTERN = re.compile(r"[\ufffd\ufffd]")  # Replacement characters

# Canonical section headings expected from the semantic parser.
# Keep in sync with the parser's canonical set; unknown headings are considered malformed.
ALLOWED_SECTION_HEADINGS = {
    "MIND",
    "HEAD",
    "EYES",
    "EARS",
    "NOSE",
    "FACE",
    "MOUTH",
    "THROAT",
    "STOMACH",
    "ABDOMEN",
    "RECTUM",
    "STOOL",
    "URINE",
    "URINARY",
    "MALE",
    "FEMALE",
    "RESPIRATORY",
    "CHEST",
    "HEART",
    "BACK",
    "EXTREMITIES",
    "LIMBS",
    "SKIN",
    "FEVER",
    "SLEEP",
    "MODALITIES",
    "DOSE",
    "CLINICAL",
    "GENERALITIES",
    "DREAMS",
    "DESIRES",
    "AVERSIONS",
}

# These headings should be extracted into the dedicated "relationships" field, not left in sections.
RELATIONSHIP_HEADINGS = {
    "RELATIONSHIPS",
    "RELATIONSHIP",
    "RELATIONS",
    "RELATION",
    "COMPARE",
    "COMPLEMENTARY",
    "ANTIDOTE",
    "ANTIDOTES",
    "INIMICAL",
    "INCOMPATIBLE",
    "FOLLOWS",
    "FOLLOWED",
    "SIMILAR",
    "COMPATIBLE",
    "COLLATERAL",
}

# Heuristic tail-words used to detect likely truncation.
TRUNCATION_TAIL_WORDS = {
    "and",
    "or",
    "with",
    "without",
    "as",
    "to",
    "of",
    "the",
    "a",
    "an",
    "in",
    "on",
    "for",
    "from",
    "by",
    "at",
    "this",
    "that",
    "which",
    "who",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "it",
    "its",
    "his",
    "her",
    "their",
    "there",
    "these",
    "those",
}


def _normalize_text(value: Optional[str]) -> str:
    if value is None:
        return ""
    normalized = unicodedata.normalize("NFC", str(value))
    return normalized.strip()


def _contains_html(text: str) -> bool:
    return bool(HTML_TAG_PATTERN.search(text))


def _contains_site_metadata(text: str) -> bool:
    return bool(SITE_METADATA_PATTERN.search(text))


def _contains_control_chars(text: str) -> bool:
    return bool(CONTROL_CHAR_PATTERN.search(text))


def _contains_malformed_unicode(text: str) -> bool:
    return bool(MALFORMED_UNICODE_PATTERN.search(text))


def _has_excessive_whitespace(text: str) -> bool:
    return bool(EXCESSIVE_SPACES_PATTERN.search(text))


def _normalize_heading_key(value: str) -> str:
    text = unicodedata.normalize("NFC", str(value))
    text = re.sub(r"\s+", " ", text).strip()
    return text.upper()


def _simplify_prefix(value: str) -> str:
    """Normalize a string for prefix comparisons (case/punct insensitive)."""
    text = unicodedata.normalize("NFC", str(value))
    text = re.sub(r"[^A-Za-z0-9]+", " ", text).strip().upper()
    return re.sub(r"\s{2,}", " ", text)


def _general_starts_with_title(general: str, full_name: str, common_name: Optional[str]) -> bool:
    g = _simplify_prefix(general)[:400]
    fn = _simplify_prefix(full_name)
    cn = _simplify_prefix(common_name) if common_name else ""

    if fn and g.startswith(fn):
        return True
    if cn and g.startswith(cn):
        return True
    if fn and cn and g.startswith((fn + " " + cn).strip()):
        return True
    return False


def _looks_truncated(text: str) -> bool:
    """Detect likely truncation: long content ending in a stopword without terminal punctuation."""
    t = (text or "").strip()
    if len(t) < 140:
        return False
    if re.search(r"[\.\!\?\;\:\)\]\"']\s*$", t):
        return False
    m = re.search(r"([A-Za-z]+)\s*$", t)
    if not m:
        return False
    return m.group(1).lower() in TRUNCATION_TAIL_WORDS


def _is_valid_url(url: str) -> bool:
    """Check if URL is properly formatted."""
    if not url:
        return False
    return bool(re.match(r'^https?://.+\..+', url))


def _check_required_field(value: Any, field_name: str) -> Optional[str]:
    """Check if a required field is present and not empty."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return f"required field '{field_name}' is empty or missing"
    return None


def validate_remedy(remedy: Dict[str, Any], seen_urls: Set[str]) -> List[str]:
    """Validate a single remedy record against all quality criteria."""
    errors: List[str] = []
    abbrev = remedy.get("abbreviation", "UNKNOWN")
    url = remedy.get("source_url", "UNKNOWN")
    identifier = f"[{abbrev} @ {url}]"

    # ============================================================
    # Basic structure validation
    # ============================================================
    if not isinstance(remedy, dict):
        errors.append(f"{identifier} invalid record type (not dict)")
        return errors

    # ============================================================
    # Required fields
    # ============================================================

    # Abbreviation
    if err := _check_required_field(abbrev, "abbreviation"):
        errors.append(f"{identifier} {err}")
    elif not ABBREVIATION_PATTERN.match(abbrev):
        errors.append(f"{identifier} malformed abbreviation (must be 2+ uppercase alphanumeric or hyphens)")

    # Source URL
    if err := _check_required_field(url, "source_url"):
        errors.append(f"{identifier} {err}")
    elif not _is_valid_url(url):
        errors.append(f"{identifier} malformed source_url")
    elif url in seen_urls:
        errors.append(f"{identifier} duplicate source_url (already seen)")
    else:
        seen_urls.add(url)

    # Full name
    full_name = remedy.get("full_name")
    if err := _check_required_field(full_name, "full_name"):
        errors.append(f"{identifier} {err}")
    else:
        full_name_clean = _normalize_text(full_name)
        # Check for metadata pollution
        if _contains_site_metadata(full_name_clean):
            errors.append(f"{identifier} full_name contains metadata/footer pollution")
        # Title normalization edge cases (e.g. chemical explanations)
        if re.search(r":\s*[^:]*=", full_name_clean):
            errors.append(f"{identifier} full_name contains formula/explanatory suffix (expected canonical title only)")
        if _contains_html(full_name_clean):
            errors.append(f"{identifier} full_name contains HTML tags")
        if _contains_control_chars(full_name_clean):
            errors.append(f"{identifier} full_name contains malformed unicode (control chars)")
        if _contains_malformed_unicode(full_name_clean):
            errors.append(f"{identifier} full_name contains replacement characters")
        if _has_excessive_whitespace(full_name_clean):
            errors.append(f"{identifier} full_name has excessive whitespace")

    # ============================================================
    # Optional fields
    # ============================================================

    # Common name (optional)
    common_name = remedy.get("common_name")
    if common_name is not None:
        if not isinstance(common_name, str):
            errors.append(f"{identifier} common_name must be string or null")
        else:
            common_name_clean = _normalize_text(common_name)
            if common_name_clean:
                if _contains_site_metadata(common_name_clean):
                    errors.append(f"{identifier} common_name contains metadata pollution")
                if _contains_html(common_name_clean):
                    errors.append(f"{identifier} common_name contains HTML tags")
                if _contains_control_chars(common_name_clean):
                    errors.append(f"{identifier} common_name contains malformed unicode")
                if _contains_malformed_unicode(common_name_clean):
                    errors.append(f"{identifier} common_name contains replacement characters")

    # Letter
    letter = remedy.get("letter")
    if letter and not isinstance(letter, str):
        errors.append(f"{identifier} letter must be string or null")
    elif letter and not re.match(r'^[A-Z]$', letter):
        errors.append(f"{identifier} letter must be single uppercase letter")

    # General (optional but usually present)
    general = remedy.get("general")
    if general is not None:
        if not isinstance(general, str):
            errors.append(f"{identifier} general must be string or null")
        else:
            general_clean = _normalize_text(general)
            if general_clean:
                if isinstance(full_name, str) and full_name.strip():
                    cn_val = common_name if isinstance(common_name, str) else None
                    if _general_starts_with_title(general_clean, full_name, cn_val):
                        errors.append(f"{identifier} general starts with title/common-name bleed")
                if _contains_site_metadata(general_clean[-200:]):  # Check end for footer leakage
                    errors.append(f"{identifier} general contains metadata/footer at end")
                if _contains_html(general_clean):
                    errors.append(f"{identifier} general contains HTML tags")
                if _contains_control_chars(general_clean):
                    errors.append(f"{identifier} general contains malformed unicode")
                if _contains_malformed_unicode(general_clean):
                    errors.append(f"{identifier} general contains replacement characters")

    # Sections (must be dict)
    sections = remedy.get("sections")
    if sections is not None:
        if not isinstance(sections, dict):
            errors.append(f"{identifier} sections must be dict")
        else:
            if not sections:
                # Empty sections dict is acceptable but unusual
                pass
            for section_name, section_content in sections.items():
                # Validate section name
                if not isinstance(section_name, str) or not section_name.strip():
                    errors.append(f"{identifier} section name is empty or invalid")
                else:
                    normalized_section = _normalize_heading_key(section_name)
                    if len(normalized_section) > 40:
                        errors.append(f"{identifier} section name too long (likely malformed heading bleed)")
                    if any(ch in normalized_section for ch in ("=", ":", "(", ")", "[" , "]")):
                        errors.append(f"{identifier} section name contains metadata/prefix fragments")
                    if normalized_section in RELATIONSHIP_HEADINGS:
                        errors.append(f"{identifier} relationships-like heading '{normalized_section}' must not appear in sections")
                    elif normalized_section not in ALLOWED_SECTION_HEADINGS:
                        errors.append(f"{identifier} section name '{normalized_section}' is not a canonical heading")

                # Validate section content
                if not isinstance(section_content, str):
                    errors.append(f"{identifier} section '{section_name}' value must be string")
                else:
                    if _contains_site_metadata(section_content[-200:]):
                        errors.append(f"{identifier} section '{section_name}' has metadata at end")
                    if _contains_html(section_content):
                        errors.append(f"{identifier} section '{section_name}' contains HTML")
                    if _contains_control_chars(section_content):
                        errors.append(f"{identifier} section '{section_name}' has malformed unicode")
                    if _contains_malformed_unicode(section_content):
                        errors.append(f"{identifier} section '{section_name}' has replacement chars")
                    if _looks_truncated(section_content):
                        errors.append(f"{identifier} section '{section_name}' appears truncated (ends mid-sentence)")

    # Relationships (optional string or null)
    relationships = remedy.get("relationships")
    if relationships is not None:
        if not isinstance(relationships, str):
            errors.append(f"{identifier} relationships must be string or null")
        else:
            relationships_clean = _normalize_text(relationships)
            if relationships_clean:
                if _contains_site_metadata(relationships_clean[-200:]):
                    errors.append(f"{identifier} relationships has metadata at end")
                if _contains_html(relationships_clean):
                    errors.append(f"{identifier} relationships contains HTML")
                if _contains_control_chars(relationships_clean):
                    errors.append(f"{identifier} relationships has malformed unicode")
                if _contains_malformed_unicode(relationships_clean):
                    errors.append(f"{identifier} relationships has replacement chars")
                # Check it's not just repeating section content
                if isinstance(sections, dict):
                    for section_content in sections.values():
                        if section_content and relationships_clean == section_content:
                            errors.append(f"{identifier} relationships duplicates a section")
                            break
    else:
        # If relationships is null but relationship markers exist in general or any section, extraction likely failed.
        relationship_markers = r"(Relationship\\s*\\.|\\bCompare\\s*:|\\bComplementary\\s*:|\\bAntidotes?\\s*:|\\bInimical\\s*:|\\bIncompatible\\s*:|\\bFollows\\s*:|\\bFollowed\\s*:)"
        if isinstance(general, str) and re.search(relationship_markers, general, re.IGNORECASE):
            errors.append(f"{identifier} relationships is null but relationship markers exist in general")
        if isinstance(sections, dict):
            for section_content in sections.values():
                if isinstance(section_content, str) and re.search(relationship_markers, section_content, re.IGNORECASE):
                    errors.append(f"{identifier} relationships is null but relationship markers exist in section content")
                    break

    return errors


def validate_remedies(data: List[Dict[str, Any]]) -> List[str]:
    """Validate entire remedies dataset."""
    issues: List[str] = []
    seen_urls: Set[str] = set()

    if not isinstance(data, list):
        issues.append("ERROR: output root is not a list")
        return issues

    if not data:
        issues.append("WARNING: dataset is empty")
        return issues

    # Validate each remedy
    for idx, remedy in enumerate(data):
        remedy_issues = validate_remedy(remedy, seen_urls)
        issues.extend(remedy_issues)

    # Summary statistics
    total_errors = len(issues)
    if total_errors == 0:
        issues.append(f"✓ VALIDATION PASSED: All {len(data)} remedies are valid")
    else:
        issues.append(f"\n✗ VALIDATION FAILED: {total_errors} issues found in {len(data)} remedies")

    return issues
