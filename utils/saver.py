import json
import os
from typing import Dict, List, Optional, Set, Tuple

from .cleaner import clean_text


def append_failed_url(file_path: str, url: str, reason: str) -> None:
    """Append a failed URL and failure reason to the log file."""
    with open(file_path, "a", encoding="utf-8") as stream:
        stream.write(f"{url} # {reason}\n")


def _normalize_optional_string(value: object) -> Optional[str]:
    if value is None:
        return None

    text = clean_text(str(value))
    return text if text else None


def load_existing_data(file_path: str) -> Tuple[List[Dict[str, object]], Set[str]]:
    """Load and validate existing remedy output for resumability."""
    if not os.path.exists(file_path):
        return [], set()

    try:
        with open(file_path, "r", encoding="utf-8") as stream:
            raw_data = json.load(stream)
    except Exception:
        return [], set()

    if not isinstance(raw_data, list):
        return [], set()

    cleaned_data: List[Dict[str, object]] = []
    seen_urls: Set[str] = set()

    for item in raw_data:
        if not isinstance(item, dict):
            continue

        source_url = item.get("source_url")
        abbreviation = item.get("abbreviation")
        full_name = item.get("full_name")
        letter = item.get("letter")
        general = item.get("general")
        sections = item.get("sections")
        relationships = item.get("relationships")

        if (
            not isinstance(source_url, str)
            or not source_url.strip()
            or source_url in seen_urls
            or not isinstance(abbreviation, str)
            or not abbreviation.strip()
            or not isinstance(full_name, str)
            or not full_name.strip()
            or not isinstance(letter, str)
            or not letter.strip()
        ):
            continue

        normalized_sections = sections if isinstance(sections, dict) else {}
        cleaned_data.append(
            {
                "abbreviation": clean_text(abbreviation),
                "full_name": clean_text(full_name),
                "common_name": _normalize_optional_string(item.get("common_name")),
                "source_url": source_url,
                "letter": clean_text(letter),
                "general": clean_text(general) if isinstance(general, str) else "",
                "sections": normalized_sections,
                "relationships": _normalize_optional_string(relationships),
            }
        )
        seen_urls.add(source_url)

    return cleaned_data, seen_urls


def save_output(data_file_path: str, sample_file_path: str, data: List[Dict[str, object]]) -> None:
    """Save the full output and an automatic sample output file."""
    with open(data_file_path, "w", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False)

    sample_data = data[:5]
    with open(sample_file_path, "w", encoding="utf-8") as stream:
        json.dump(sample_data, stream, indent=2, ensure_ascii=False)
