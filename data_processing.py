"""
SpendSense — Data Processing & CSV Validation Module.

This module implements Milestone 1 requirements:
1. Validating CSV file-level schema against the fixed SpendSense contract:
   - Required headers: Date, Description, Amount, Type
   - Detection of duplicate, missing, or unexpected headers
   - Detection of header collision with the reserved extra-column restkey
2. Explicit detection of structural row errors:
   - Rows with extra columns (via reserved restkey __EXTRA_COLUMNS__)
   - Rows with missing columns (via None values in required fields)
3. Validating field-level rules:
   - Date: valid calendar date in exact YYYY-MM-DD format
   - Description: non-empty, non-whitespace string; preserves original text
   - Amount: positive decimal INR amount with at most two meaningful decimal places
   - Type: DEBIT or CREDIT (case and surrounding whitespace normalized)
4. Converting money directly to integer paise using decimal.Decimal (never float).
"""

from decimal import Decimal, InvalidOperation
import csv
import datetime
from pathlib import Path
from typing import Any

# Fixed header contract required by SpendSense
EXPECTED_HEADERS = ("Date", "Description", "Amount", "Type")

# Dedicated reserved key used to detect rows with extra columns in csv.DictReader
RESERVED_RESTKEY = "__EXTRA_COLUMNS__"


class CSVFileError(ValueError):
    """Raised for file-level CSV failures (empty file, invalid headers, parser errors)."""
    pass


class CSVFileNotFoundError(CSVFileError, FileNotFoundError):
    """Raised when the target CSV file does not exist."""
    pass


# Maximum supported integer paise that can be stored in SQLite's signed 64-bit INTEGER (2^63 - 1)
MAX_PAISE_INTEGER: int = 9223372036854775807


def to_paise(amount_text: str) -> int:
    """
    Validate positive monetary text and return exact integer paise.

    Rules:
    - Must be a non-empty string.
    - Parse directly with decimal.Decimal (never convert to float first).
    - Reject scientific notation (e.g., '1e2').
    - Reject non-finite values (NaN, Infinity, -Infinity).
    - Reject zero and negative amounts.
    - Reject amounts not exactly representable to two decimal places (e.g., '12.345').
    - Accept values like '10.50' -> 1050 and '12.340' -> 1234.
    - Inspect digits directly to prevent precision loss on very long decimal inputs.
    - Reject amounts whose paise value exceeds SQLite's maximum 64-bit integer limit.
    """
    if not isinstance(amount_text, str):
        raise ValueError("amount must be a string")

    text = amount_text.strip()
    if not text:
        raise ValueError("amount cannot be empty")

    # Scientific notation is not standard for currency amounts
    if "e" in text.lower():
        raise ValueError("scientific notation is not allowed for amounts")

    try:
        decimal_val = Decimal(text)
    except InvalidOperation:
        raise ValueError(f"invalid amount format: '{amount_text}' is not a valid decimal number")

    if not decimal_val.is_finite():
        raise ValueError("amount must be a finite number")

    if decimal_val <= Decimal(0):
        raise ValueError("amount must be positive")

    sign, digits, exp = decimal_val.as_tuple()

    # Exact check for at most two decimal places without Decimal context precision loss:
    # If exponent is less than -2, check that all digits beyond 10^-2 are zero.
    if exp < -2:
        num_trailing = -exp - 2
        if len(digits) <= num_trailing:
            # All non-zero digits are placed beyond 10^-2 (e.g. 0.001)
            if any(d != 0 for d in digits):
                raise ValueError("amount has more than two decimal places")
            trimmed_digits = (0,)
        else:
            # The last num_trailing digits correspond to positions 10^-3 and smaller
            if any(d != 0 for d in digits[-num_trailing:]):
                raise ValueError("amount has more than two decimal places")
            trimmed_digits = digits[:-num_trailing]
        effective_exp = -2
    else:
        trimmed_digits = digits
        effective_exp = exp

    # Convert to exact integer paise using integer arithmetic (never float or context multiplication)
    unscaled_int = int("".join(str(d) for d in trimmed_digits)) if trimmed_digits else 0
    shift = effective_exp + 2
    paise_val = unscaled_int * (10 ** shift)

    if paise_val <= 0:
        raise ValueError("amount must be positive")

    if paise_val > MAX_PAISE_INTEGER:
        raise ValueError(
            f"amount exceeds maximum supported value ({MAX_PAISE_INTEGER} paise)"
        )

    return paise_val


def validate_date(date_text: str) -> str:
    """Validate that date_text is an exact calendar date in YYYY-MM-DD format."""
    if not isinstance(date_text, str):
        raise ValueError("date must be a string")

    date_str = date_text.strip()
    if len(date_str) != 10:
        raise ValueError("invalid date: must be in exact YYYY-MM-DD format")

    try:
        parsed_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        if parsed_date.strftime("%Y-%m-%d") != date_str:
            raise ValueError("invalid date: must be in exact YYYY-MM-DD format")
    except (ValueError, TypeError):
        raise ValueError(f"invalid date: '{date_text}' is not a valid calendar date in YYYY-MM-DD format")

    return date_str


def validate_description(description_text: str) -> str:
    """Validate that description is non-empty after trimming whitespace."""
    if not isinstance(description_text, str) or not description_text.strip():
        raise ValueError("empty description")
    return description_text


def validate_type(type_text: str) -> str:
    """Normalize and validate transaction type as 'DEBIT' or 'CREDIT'."""
    if not isinstance(type_text, str):
        raise ValueError("Type must be DEBIT or CREDIT")

    norm_type = type_text.strip().upper()
    if norm_type not in ("DEBIT", "CREDIT"):
        raise ValueError("Type must be DEBIT or CREDIT")

    return norm_type


def _parse_csv_stream(f) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Parse and validate an open CSV text stream."""
    try:
        reader = csv.DictReader(f, restkey=RESERVED_RESTKEY, restval=None, strict=True)
        raw_fieldnames = reader.fieldnames
    except csv.Error as e:
        raise CSVFileError(f"Malformed CSV parser failure reading header: {e}") from e

    # Check for empty file or missing header row
    if not raw_fieldnames:
        raise CSVFileError("CSV file is empty or contains no header row")

    raw_headers = list(raw_fieldnames)

    # Check for empty column name in header
    if any(h is None or h.strip() == "" for h in raw_headers):
        raise CSVFileError("CSV header contains an empty column name")

    # Check for reserved restkey collision
    if any(h.strip() == RESERVED_RESTKEY for h in raw_headers if h):
        raise CSVFileError(f"Header contains reserved restkey name: '{RESERVED_RESTKEY}'")

    # Strip surrounding whitespace from header names
    normalized_headers = [h.strip() for h in raw_headers]

    # Check for duplicate headers
    if len(normalized_headers) != len(set(normalized_headers)):
        raise CSVFileError(f"Duplicate header names detected in CSV: {normalized_headers}")

    # Check for missing required headers
    missing_headers = [col for col in EXPECTED_HEADERS if col not in normalized_headers]
    if missing_headers:
        raise CSVFileError(f"Missing required header(s): {missing_headers}")

    # Check for unexpected headers
    unexpected_headers = [col for col in normalized_headers if col not in EXPECTED_HEADERS]
    if unexpected_headers:
        raise CSVFileError(
            f"Unexpected header(s) in CSV: {unexpected_headers}. Expected exactly: {list(EXPECTED_HEADERS)}"
        )

    # Update reader fieldnames to normalized names so row dictionaries use clean keys
    reader.fieldnames = normalized_headers

    accepted_records: list[dict[str, Any]] = []
    rejected_records: list[dict[str, Any]] = []

    try:
        for record_number, row in enumerate(reader, start=2):
            # 1. Structural check: Extra fields present
            if RESERVED_RESTKEY in row and row[RESERVED_RESTKEY]:
                rejected_records.append({
                    "record_number": record_number,
                    "line_number": reader.line_num,
                    "reason": "Row has extra columns",
                })
                continue

            # 2. Structural check: Missing fields present (None values for required columns)
            if any(row.get(col) is None for col in EXPECTED_HEADERS):
                rejected_records.append({
                    "record_number": record_number,
                    "line_number": reader.line_num,
                    "reason": "Row has missing columns",
                })
                continue

            # 3. Field validation: Date
            try:
                date_val = validate_date(row["Date"])
            except ValueError as e:
                rejected_records.append({
                    "record_number": record_number,
                    "line_number": reader.line_num,
                    "reason": str(e),
                })
                continue

            # 4. Field validation: Description
            try:
                desc_val = validate_description(row["Description"])
            except ValueError as e:
                rejected_records.append({
                    "record_number": record_number,
                    "line_number": reader.line_num,
                    "reason": str(e),
                })
                continue

            # 5. Field validation: Amount
            try:
                paise_val = to_paise(row["Amount"])
            except ValueError as e:
                rejected_records.append({
                    "record_number": record_number,
                    "line_number": reader.line_num,
                    "reason": str(e),
                })
                continue

            # 6. Field validation: Type
            try:
                type_val = validate_type(row["Type"])
            except ValueError as e:
                rejected_records.append({
                    "record_number": record_number,
                    "line_number": reader.line_num,
                    "reason": str(e),
                })
                continue

            # Accepted valid record
            accepted_records.append({
                "transaction_date": date_val,
                "description": desc_val,
                "transaction_type": type_val,
                "amount_paise": paise_val,
            })

    except csv.Error as e:
        raise CSVFileError(f"Malformed CSV parser failure at line {reader.line_num}: {e}") from e

    return accepted_records, rejected_records


def load_and_validate_csv(path_or_file: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Load a CSV file and return (accepted_records, rejected_records).

    Accepts a filepath (str or Path) or an open text stream.
    Raises:
    - CSVFileNotFoundError if the file does not exist.
    - CSVFileError if the file is unreadable, empty, has an invalid header, or has malformed CSV structure.
    """
    if hasattr(path_or_file, "read"):
        try:
            return _parse_csv_stream(path_or_file)
        except UnicodeDecodeError as e:
            raise CSVFileError(f"Cannot read CSV stream: {e}") from e

    try:
        with open(path_or_file, mode="r", encoding="utf-8-sig", newline="") as f:
            return _parse_csv_stream(f)
    except FileNotFoundError as e:
        raise CSVFileNotFoundError(f"CSV file not found: {path_or_file}") from e
    except (OSError, UnicodeDecodeError) as e:
        raise CSVFileError(f"Cannot read CSV file: {path_or_file} ({e})") from e
