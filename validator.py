"""
Record validation utilities.

Provides validation that:
- Checks for required fields (title, content, url)
- Validates URL format
- Checks content length minimums
- Flags invalid records with reasons
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

REQUIRED_FIELDS = ("title", "content", "url")

DEFAULT_MIN_LENGTHS = {
    "title": 1,
    "content": 1,
}

# URL pattern for basic validation (http/https)
URL_PATTERN = re.compile(
    r"^https?://"
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"
    r"localhost|"
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
    r"(?::\d+)?"
    r"(?:/?|[/?]\S+)$",
    re.IGNORECASE,
)


# -----------------------------------------------------------------------------
# Validation Result
# -----------------------------------------------------------------------------


@dataclass
class ValidationResult:
    """Result of validating a single record."""

    is_valid: bool
    reasons: List[str] = field(default_factory=list)

    def add_reason(self, reason: str) -> None:
        """Add an invalidity reason."""
        self.reasons.append(reason)

    def __str__(self) -> str:
        status = "Valid" if self.is_valid else "Invalid"
        if self.reasons:
            return f"{status}: {'; '.join(self.reasons)}"
        return status


# -----------------------------------------------------------------------------
# Validation Functions
# -----------------------------------------------------------------------------


def validate_url(url: str) -> bool:
    """
    Validate URL format. Accepts http and https URLs.

    Args:
        url: URL string to validate

    Returns:
        True if URL format is valid.
    """
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    if not url:
        return False
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            return False
        if result.scheme not in ("http", "https"):
            return False
        # Additional regex check for common URL structure
        return bool(URL_PATTERN.match(url))
    except Exception:
        return False


def validate_required_fields(
    record: Dict[str, Any],
    required: Optional[tuple] = None,
) -> List[str]:
    """
    Check that all required fields are present and non-empty.

    Args:
        record: Dictionary representing a record
        required: Tuple of required field names (default: title, content, url)

    Returns:
        List of reasons for missing/invalid required fields.
    """
    required = required or REQUIRED_FIELDS
    reasons = []
    for field_name in required:
        if field_name not in record:
            reasons.append(f"Missing required field: '{field_name}'")
        elif record[field_name] is None:
            reasons.append(f"Required field '{field_name}' is None")
        elif isinstance(record[field_name], str) and not record[field_name].strip():
            reasons.append(f"Required field '{field_name}' is empty")
    return reasons


def validate_content_length(
    record: Dict[str, Any],
    min_lengths: Optional[Dict[str, int]] = None,
) -> List[str]:
    """
    Check that content and title meet minimum length requirements.

    Args:
        record: Dictionary with 'title' and 'content' keys
        min_lengths: Dict mapping field names to minimum lengths

    Returns:
        List of reasons when length constraints are violated.
    """
    min_lengths = min_lengths or DEFAULT_MIN_LENGTHS
    reasons = []
    for field_name, min_len in min_lengths.items():
        if field_name not in record:
            continue
        value = record[field_name]
        if value is None:
            continue
        length = len(str(value).strip())
        if length < min_len:
            reasons.append(
                f"Field '{field_name}' length {length} is below minimum {min_len}"
            )
    return reasons


def validate_record(
    record: Dict[str, Any],
    required_fields: Optional[tuple] = None,
    min_lengths: Optional[Dict[str, int]] = None,
) -> ValidationResult:
    """
    Run full validation on a record. Flags invalid records with reasons.

    Args:
        record: Dictionary with title, content, url and optional fields
        required_fields: Override default required fields
        min_lengths: Override default minimum lengths per field

    Returns:
        ValidationResult with is_valid flag and list of reasons.
    """
    reasons = []
    required = required_fields or REQUIRED_FIELDS
    mins = min_lengths or DEFAULT_MIN_LENGTHS

    # Required fields
    reasons.extend(validate_required_fields(record, required))

    # URL format (only if url is present)
    if "url" in record and record["url"] is not None:
        url_val = str(record["url"]).strip()
        if url_val and not validate_url(url_val):
            url_display = f"{url_val[:50]}..." if len(url_val) > 50 else url_val
            reasons.append(f"Invalid URL format: '{url_display}'")

    # Content length
    reasons.extend(validate_content_length(record, mins))

    is_valid = len(reasons) == 0
    return ValidationResult(is_valid=is_valid, reasons=reasons)


def validate_records(
    records: List[Dict[str, Any]],
    required_fields: Optional[tuple] = None,
    min_lengths: Optional[Dict[str, int]] = None,
) -> List[ValidationResult]:
    """
    Validate a list of records. Returns one ValidationResult per record.

    Args:
        records: List of record dictionaries
        required_fields: Override default required fields
        min_lengths: Override default minimum lengths

    Returns:
        List of ValidationResult in same order as input.
    """
    return [
        validate_record(r, required_fields, min_lengths)
        for r in records
    ]


def get_invalid_records(
    records: List[Dict[str, Any]],
    required_fields: Optional[tuple] = None,
    min_lengths: Optional[Dict[str, int]] = None,
) -> List[tuple]:
    """
    Return only invalid records with their validation reasons.

    Returns:
        List of (record_index, record, ValidationResult) for invalid records.
    """
    results = validate_records(records, required_fields, min_lengths)
    invalid = []
    for i, (record, result) in enumerate(zip(records, results)):
        if not result.is_valid:
            invalid.append((i, record, result))
    return invalid


# -----------------------------------------------------------------------------
# Standalone file I/O (when run as script)
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    from collections import Counter
    from pathlib import Path

    base_path = Path(__file__).parent
    input_path = base_path / "sample_data.json"
    report_path = base_path / "quality_report.txt"

    with open(input_path, encoding="utf-8") as f:
        records = json.load(f)
    if not isinstance(records, list):
        records = [records]

    total = len(records)
    results = [validate_record(r) for r in records]
    valid_count = sum(1 for r in results if r.is_valid)
    invalid_count = total - valid_count

    field_names = ("title", "content", "url", "date", "author", "tags")
    completeness = {f: 0 for f in field_names}
    for record in records:
        for field in field_names:
            val = record.get(field)
            if val is not None:
                if isinstance(val, list) or (isinstance(val, str) and val.strip()):
                    completeness[field] += 1

    failure_counter: Counter = Counter()
    for r in results:
        for reason in r.reasons:
            failure_counter[reason] += 1

    report_lines = [
        "=" * 60,
        "DATA QUALITY REPORT",
        "=" * 60,
        "",
        f"Total records: {total}",
        f"Valid: {valid_count}",
        f"Invalid: {invalid_count}",
        "",
        "-" * 60,
        "Field completeness percentages",
        "-" * 60,
    ]
    for field in field_names:
        pct = (completeness[field] / total * 100) if total else 0
        report_lines.append(f"  {field}: {pct:.1f}%")
    report_lines.extend([
        "",
        "-" * 60,
        "Common validation failures",
        "-" * 60,
    ])
    if failure_counter:
        for reason, count in failure_counter.most_common():
            report_lines.append(f"  [{count}x] {reason}")
    else:
        report_lines.append("  (none)")
    report_lines.extend(["", "=" * 60])

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print(f"Validated {total} records -> {report_path.name} (Valid: {valid_count}, Invalid: {invalid_count})")
