import re
from utils.cleaner import clean_text

SECTION_HEADING_PATTERN = re.compile(
    r'^\s*(?P<heading>[A-Za-z][A-Za-z0-9\s\-\&/()]+?)\s*(?:\.\s*[-]{1,}|[-]{1,}\s*\.?|[-]{2,}|\.{2,})\s*(?P<content>.*)$',
    re.IGNORECASE,
)

test_cases = [
    'Mind.-- Great fear, anxiety, and worry accompany every ailment, however trivial.',
    'Head.--',
    'Symptom.-- Content here',
    'Dose.-- First to third potency.',
    'Abdominal.-- Cramping pains',
]

for text in test_cases:
    cleaned = clean_text(text)
    match = SECTION_HEADING_PATTERN.match(cleaned)
    if match:
        print(f"✓ {repr(cleaned[:50])}")
        print(f"  heading={repr(match.group('heading'))}")
        print(f"  content={repr(match.group('content')[:50] if match.group('content') else '')}")
    else:
        print(f"✗ {repr(cleaned[:50])}")
