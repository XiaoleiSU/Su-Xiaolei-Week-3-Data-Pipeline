"""
Text and data cleaning utilities.

Provides functions to:
- Remove extra whitespace and HTML artifacts
- Normalize text encoding
- Standardize date formats to ISO format
- Handle special characters appropriately
"""

import re
import unicodedata
from html.parser import HTMLParser
from datetime import datetime
from typing import Optional


# -----------------------------------------------------------------------------
# HTML Cleaning
# -----------------------------------------------------------------------------


class HTMLTagStripper(HTMLParser):
    """Strip HTML tags and return text content."""

    def __init__(self):
        super().__init__()
        self.text_parts = []

    def handle_data(self, data: str) -> None:
        self.text_parts.append(data)

    def get_text(self) -> str:
        return "".join(self.text_parts)


def remove_html_tags(text: str) -> str:
    """Remove HTML tags from text."""
    if not text or not isinstance(text, str):
        return str(text) if text is not None else ""
    stripper = HTMLTagStripper()
    try:
        stripper.feed(text)
        return stripper.get_text()
    except Exception:
        # Fallback: simple regex-based removal
        return re.sub(r"<[^>]+>", "", text)


def remove_html_artifacts(text: str) -> str:
    """
    Remove HTML artifacts: tags, entities, and common markup residue.
    """
    if not text or not isinstance(text, str):
        return str(text) if text is not None else ""
    # Decode common HTML entities
    replacements = {
        "&nbsp;": " ",
        "&amp;": "&",
        "&lt;": "<",
        "&gt;": ">",
        "&quot;": '"',
        "&#39;": "'",
        "&apos;": "'",
    }
    result = text
    for entity, char in replacements.items():
        result = result.replace(entity, char)
    # Handle numeric entities like &#160; or &#x20;
    result = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), result)
    result = re.sub(r"&#x([0-9a-fA-F]+);", lambda m: chr(int(m.group(1), 16)), result)
    return remove_html_tags(result)


# -----------------------------------------------------------------------------
# Whitespace Cleaning
# -----------------------------------------------------------------------------


def remove_extra_whitespace(text: str) -> str:
    """
    Collapse multiple spaces/newlines to single space and strip outer whitespace.
    """
    if not text or not isinstance(text, str):
        return str(text) if text is not None else ""
    result = re.sub(r"\s+", " ", text)
    return result.strip()


# -----------------------------------------------------------------------------
# Text Encoding Normalization
# -----------------------------------------------------------------------------


def normalize_encoding(text: str) -> str:
    """
    Normalize unicode text to NFC form and handle common encoding issues.
    """
    if not text or not isinstance(text, str):
        return str(text) if text is not None else ""
    normalized = unicodedata.normalize("NFC", text)
    # Replace common problematic characters from mojibake
    replacements = {
        "\u00a0": " ",  # Non-breaking space
        "\ufeff": "",   # BOM
        "\u200b": "",   # Zero-width space
        "\u200c": "",   # Zero-width non-joiner
        "\u200d": "",   # Zero-width joiner
        "\ufeff": "",   # BOM (duplicate for clarity)
    }
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    return normalized


# -----------------------------------------------------------------------------
# Special Characters Handling
# -----------------------------------------------------------------------------


def handle_special_characters(
    text: str,
    replace_control: bool = True,
    keep_printable_only: bool = False,
    replace_curly_quotes: bool = True,
) -> str:
    """
    Handle special characters appropriately.

    Args:
        text: Input text
        replace_control: Replace control characters with space
        keep_printable_only: Keep only printable ASCII/unicode (stricter)
        replace_curly_quotes: Replace curly quotes with straight quotes
    """
    if not text or not isinstance(text, str):
        return str(text) if text is not None else ""
    result = text
    if replace_curly_quotes:
        curly_map = {
            "\u2018": "'",
            "\u2019": "'",
            "\u201c": '"',
            "\u201d": '"',
            "\u2013": "-",
            "\u2014": "-",
        }
        for old, new in curly_map.items():
            result = result.replace(old, new)
    if replace_control:
        result = "".join(
            c if unicodedata.category(c) != "Cc" or c in "\n\r\t" else " "
            for c in result
        )
    if keep_printable_only:
        result = "".join(c for c in result if c.isprintable() or c in "\n\r\t")
    return result


# -----------------------------------------------------------------------------
# Date Format Standardization
# -----------------------------------------------------------------------------

# Common date format patterns (regex, strptime format)
DATE_PATTERNS = [
    (r"(\d{4})-(\d{2})-(\d{2})", "%Y-%m-%d"),
    (r"(\d{2})/(\d{2})/(\d{4})", "%m/%d/%Y"),
    (r"(\d{2})-(\d{2})-(\d{4})", "%d-%m-%Y"),
    (r"(\d{2})\.(\d{2})\.(\d{4})", "%d.%m.%Y"),
    (r"(\d{4})/(\d{2})/(\d{2})", "%Y/%m/%d"),
    (r"(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{4})", None),
    (r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})", None),
    (r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})", None),
]

MONTH_NAMES = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _parse_month_name(month_str: str) -> int:
    """Get month number from abbreviated or full month name."""
    key = month_str.lower()[:3]
    return MONTH_NAMES.get(key, 1)


def standardize_date(date_str: str) -> Optional[str]:
    """
    Convert various date formats to ISO format (YYYY-MM-DD).

    Supports:
    - YYYY-MM-DD
    - MM/DD/YYYY, DD/MM/YYYY
    - DD.MM.YYYY
    - Month names (e.g. Jan 15, 2024; 15 January 2024)

    Returns:
        ISO date string (YYYY-MM-DD) or None if parsing fails.
    """
    if not date_str or not isinstance(date_str, str):
        return None
    date_str = date_str.strip()
    # Try standard strptime formats first
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d.%m.%Y",
        "%m-%d-%Y",
        "%B %d, %Y",   # January 15, 2024
        "%b %d, %Y",   # Jan 15, 2024
        "%d %B %Y",    # 15 January 2024
        "%d %b %Y",    # 15 Jan 2024
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Try month-name patterns
    month_match = re.search(
        r"(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{4})",
        date_str,
        re.I,
    )
    if month_match:
        day, month, year = int(month_match.group(1)), month_match.group(2), int(month_match.group(3))
        month_num = _parse_month_name(month)
        try:
            return datetime(year, month_num, day).strftime("%Y-%m-%d")
        except ValueError:
            pass
    month_match2 = re.search(
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})",
        date_str,
        re.I,
    )
    if month_match2:
        month, day, year = month_match2.group(1), int(month_match2.group(2)), int(month_match2.group(3))
        month_num = _parse_month_name(month)
        try:
            return datetime(year, month_num, day).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


# -----------------------------------------------------------------------------
# Record Cleaning
# -----------------------------------------------------------------------------


def clean_record(record: dict) -> dict:
    """
    Apply full cleaning to a single record. Returns a new dict.
    Cleans title, content, author, date, tags, and url.
    """
    cleaned = record.copy()
    for field in ("title", "content", "author"):
        if field in cleaned and cleaned[field] is not None:
            cleaned[field] = clean_text(str(cleaned[field]))
    if "date" in cleaned and cleaned["date"] is not None:
        standardized = standardize_date(str(cleaned["date"]))
        cleaned["date"] = standardized if standardized else cleaned["date"]
    if "tags" in cleaned and isinstance(cleaned["tags"], list):
        cleaned["tags"] = [clean_text(str(t)) for t in cleaned["tags"] if t is not None]
    if "url" in cleaned and cleaned["url"] is not None:
        cleaned["url"] = str(cleaned["url"]).strip() or None
    return cleaned


# -----------------------------------------------------------------------------
# Combined Cleaning
# -----------------------------------------------------------------------------


def clean_text(
    text: str,
    remove_html: bool = True,
    remove_extra_spaces: bool = True,
    normalize_enc: bool = True,
    handle_special: bool = True,
) -> str:
    """
    Apply a full cleaning pipeline to text.

    Args:
        text: Input text
        remove_html: Remove HTML tags and entities
        remove_extra_spaces: Collapse and trim whitespace
        normalize_enc: Normalize unicode encoding
        handle_special: Handle special characters (curly quotes, control chars)

    Returns:
        Cleaned text
    """
    if not text or not isinstance(text, str):
        return str(text) if text is not None else ""
    result = text
    if remove_html:
        result = remove_html_artifacts(result)
    if normalize_enc:
        result = normalize_encoding(result)
    if handle_special:
        result = handle_special_characters(result)
    if remove_extra_spaces:
        result = remove_extra_whitespace(result)
    return result


# -----------------------------------------------------------------------------
# Standalone file I/O (when run as script)
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    from pathlib import Path

    base_path = Path(__file__).parent
    input_path = base_path / "sample_data.json"
    output_path = base_path / "cleaned_output.json"

    with open(input_path, encoding="utf-8") as f:
        records = json.load(f)
    if not isinstance(records, list):
        records = [records]

    cleaned = [clean_record(r) for r in records]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2, ensure_ascii=False)
    print(f"Cleaned {len(cleaned)} records -> {output_path.name}")
