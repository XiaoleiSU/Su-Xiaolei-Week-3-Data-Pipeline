"""
Data pipeline: load, clean, validate, and report.

Loads sample_data.json, cleans records using cleaner.py, validates using validator.py,
outputs cleaned_output.json and quality_report.txt.
"""

import json
from collections import Counter
from pathlib import Path

from cleaner import clean_text, standardize_date
from validator import validate_record, ValidationResult


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

INPUT_FILE = "sample_data.json"
CLEANED_OUTPUT_FILE = "cleaned_output.json"
QUALITY_REPORT_FILE = "quality_report.txt"
RECORD_LIMIT = 10  # Process first N records (set to None for all)


# -----------------------------------------------------------------------------
# Cleaning
# -----------------------------------------------------------------------------


def clean_record(record: dict) -> dict:
    """Apply cleaning to a single record. Returns a new dict."""
    cleaned = record.copy()
    # Clean text fields
    for field in ("title", "content", "author"):
        if field in cleaned and cleaned[field] is not None:
            cleaned[field] = clean_text(str(cleaned[field]))
    # Standardize date
    if "date" in cleaned and cleaned["date"] is not None:
        standardized = standardize_date(str(cleaned["date"]))
        cleaned["date"] = standardized if standardized else cleaned["date"]
    # Clean tags (array of strings)
    if "tags" in cleaned and isinstance(cleaned["tags"], list):
        cleaned["tags"] = [clean_text(str(t)) for t in cleaned["tags"] if t is not None]
    # URL: strip whitespace only (do not alter structure)
    if "url" in cleaned and cleaned["url"] is not None:
        cleaned["url"] = str(cleaned["url"]).strip() or None
    return cleaned


# -----------------------------------------------------------------------------
# Pipeline
# -----------------------------------------------------------------------------


def run_pipeline() -> None:
    """Run the full data pipeline."""
    base_path = Path(__file__).parent
    input_path = base_path / INPUT_FILE
    output_path = base_path / CLEANED_OUTPUT_FILE
    report_path = base_path / QUALITY_REPORT_FILE

    # 1. Load data
    print("Loading data...")
    with open(input_path, encoding="utf-8") as f:
        raw_records = json.load(f)

    if not isinstance(raw_records, list):
        raw_records = [raw_records]

    # Limit to first N records if specified
    if RECORD_LIMIT is not None:
        raw_records = raw_records[:RECORD_LIMIT]

    total_records = len(raw_records)
    print(f"  Loaded {total_records} records from {INPUT_FILE}\n")

    # 2. Clean all records
    print("Cleaning records...")
    cleaned_records = [clean_record(r) for r in raw_records]
    print(f"  Cleaned {len(cleaned_records)} records\n")

    # 3. Validate cleaned records
    print("Validating records...")
    validation_results = [validate_record(r) for r in cleaned_records]
    valid_count = sum(1 for r in validation_results if r.is_valid)
    invalid_count = total_records - valid_count
    print(f"  Valid: {valid_count}, Invalid: {invalid_count}\n")

    # 4. Build cleaned output (add validation status to each record)
    output_data = []
    for record, result in zip(cleaned_records, validation_results):
        out = record.copy()
        out["_valid"] = result.is_valid
        if not result.is_valid:
            out["_validation_reasons"] = result.reasons
        output_data.append(out)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    print(f"Wrote {CLEANED_OUTPUT_FILE}\n")

    # 5. Generate quality report
    field_names = ("title", "content", "url", "date", "author", "tags")
    completeness = {f: 0 for f in field_names}

    for record in cleaned_records:
        for field in field_names:
            val = record.get(field)
            if val is not None:
                if isinstance(val, list):
                    completeness[field] += 1  # Consider non-null list as present
                elif isinstance(val, str) and val.strip():
                    completeness[field] += 1

    failure_counter: Counter = Counter()
    for result in validation_results:
        for reason in result.reasons:
            failure_counter[reason] += 1

    report_lines = [
        "=" * 60,
        "DATA QUALITY REPORT",
        "=" * 60,
        "",
        f"Total records: {total_records}",
        f"Valid: {valid_count}",
        f"Invalid: {invalid_count}",
        "",
        "-" * 60,
        "Field completeness percentages",
        "-" * 60,
    ]

    for field in field_names:
        pct = (completeness[field] / total_records * 100) if total_records else 0
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
    print(f"Wrote {QUALITY_REPORT_FILE}\n")

    # 6. Console summary
    print("=" * 50)
    print("SUMMARY STATISTICS")
    print("=" * 50)
    print(f"  Total records:    {total_records}")
    print(f"  Valid:            {valid_count} ({valid_count / total_records * 100:.1f}%)")
    print(f"  Invalid:          {invalid_count} ({invalid_count / total_records * 100:.1f}%)")
    print()
    print("Field completeness:")
    for field in field_names:
        pct = (completeness[field] / total_records * 100) if total_records else 0
        print(f"  {field}: {completeness[field]}/{total_records} ({pct:.1f}%)")
    print()
    if failure_counter:
        print("Top validation failures:")
        for reason, count in failure_counter.most_common(5):
            print(f"  - {count}x: {reason[:60]}{'...' if len(reason) > 60 else ''}")
    print("=" * 50)


# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    run_pipeline()
