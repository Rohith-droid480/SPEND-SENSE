"""
SpendSense — Milestone 1 Tests: CSV Schema Validation and Money Parsing.

Covers:
A. Valid input (single/multiple records, counts, field preservation)
B. Header and row structure (missing, duplicate, unexpected headers, restkey collision,
   extra/missing fields, empty/header-only/missing files, csv.Error)
C. Transaction fields (dates, leap years, descriptions, DEBIT/CREDIT normalization)
D. Monetary conversion (to_paise precision, non-finite, zero, negative, no float, no rounding)
E. Error isolation (adjacent row safety, record numbers, rejection reasons)
"""

from decimal import Decimal
import io
import pytest

from data_processing import (
    CSVFileError,
    CSVFileNotFoundError,
    EXPECTED_HEADERS,
    MAX_PAISE_INTEGER,
    RESERVED_RESTKEY,
    load_and_validate_csv,
    to_paise,
    validate_date,
    validate_description,
    validate_type,
)


# ============================================================================
# Section A: Valid Input
# ============================================================================

def test_valid_csv_single_row(tmp_path):
    """Test importing a single valid CSV record."""
    csv_file = tmp_path / "valid_single.csv"
    csv_file.write_text(
        "Date,Description,Amount,Type\n"
        "2026-10-03,DMART STORE 018,125.50,DEBIT\n",
        encoding="utf-8",
    )

    accepted, rejected = load_and_validate_csv(csv_file)

    assert len(accepted) == 1
    assert len(rejected) == 0
    record = accepted[0]
    assert record["transaction_date"] == "2026-10-03"
    assert record["description"] == "DMART STORE 018"
    assert record["transaction_type"] == "DEBIT"
    assert record["amount_paise"] == 12550
    assert isinstance(record["amount_paise"], int)


def test_valid_csv_multiple_rows(tmp_path):
    """Test multiple valid records including DEBIT, CREDIT, and integer rupees."""
    csv_file = tmp_path / "valid_multiple.csv"
    csv_file.write_text(
        "Date,Description,Amount,Type\n"
        "2026-10-01,Salary,50000.00,CREDIT\n"
        "2026-10-02,Uber Trip,350.00,DEBIT\n"
        "2026-10-03,Refund Reversal,150.75,CREDIT\n",
        encoding="utf-8",
    )

    accepted, rejected = load_and_validate_csv(csv_file)

    assert len(accepted) == 3
    assert len(rejected) == 0
    assert accepted[0]["amount_paise"] == 5000000
    assert accepted[0]["transaction_type"] == "CREDIT"
    assert accepted[1]["amount_paise"] == 35000
    assert accepted[1]["transaction_type"] == "DEBIT"
    assert accepted[2]["amount_paise"] == 15075
    assert accepted[2]["transaction_type"] == "CREDIT"


def test_valid_csv_header_whitespace_tolerance(tmp_path):
    """Test that optional surrounding whitespace in header names is stripped."""
    csv_file = tmp_path / "header_spaces.csv"
    csv_file.write_text(
        " Date , Description , Amount , Type \n"
        "2026-10-01,Groceries,10.50,DEBIT\n",
        encoding="utf-8",
    )

    accepted, rejected = load_and_validate_csv(csv_file)

    assert len(accepted) == 1
    assert len(rejected) == 0
    assert accepted[0]["description"] == "Groceries"
    assert accepted[0]["amount_paise"] == 1050


# ============================================================================
# Section B: Header and Row Structure
# ============================================================================

def test_missing_header_raises_csv_file_error(tmp_path):
    """Test that a missing required column ('Type') raises CSVFileError."""
    csv_file = tmp_path / "missing_header.csv"
    csv_file.write_text(
        "Date,Description,Amount\n"
        "2026-10-01,Groceries,10.50\n",
        encoding="utf-8",
    )

    with pytest.raises(CSVFileError) as exc_info:
        load_and_validate_csv(csv_file)
    assert "Missing required header" in str(exc_info.value)
    assert "Type" in str(exc_info.value)


def test_duplicate_header_raises_csv_file_error(tmp_path):
    """Test that duplicate header names raise CSVFileError."""
    csv_file = tmp_path / "duplicate_header.csv"
    csv_file.write_text(
        "Date,Description,Amount,Amount\n"
        "2026-10-01,Groceries,10.50,10.50\n",
        encoding="utf-8",
    )

    with pytest.raises(CSVFileError) as exc_info:
        load_and_validate_csv(csv_file)
    assert "Duplicate header names detected" in str(exc_info.value)


def test_unexpected_header_raises_csv_file_error(tmp_path):
    """Test that extra / unsupported columns in the header raise CSVFileError."""
    csv_file = tmp_path / "unexpected_header.csv"
    csv_file.write_text(
        "Date,Description,Amount,Type,ExtraColumn\n"
        "2026-10-01,Groceries,10.50,DEBIT,foo\n",
        encoding="utf-8",
    )

    with pytest.raises(CSVFileError) as exc_info:
        load_and_validate_csv(csv_file)
    assert "Unexpected header(s) in CSV" in str(exc_info.value)


def test_header_collision_with_reserved_restkey(tmp_path):
    """Test that a header named identical to the reserved restkey is rejected."""
    csv_file = tmp_path / "restkey_collision.csv"
    csv_file.write_text(
        f"Date,Description,Amount,{RESERVED_RESTKEY}\n"
        "2026-10-01,Groceries,10.50,foo\n",
        encoding="utf-8",
    )

    with pytest.raises(CSVFileError) as exc_info:
        load_and_validate_csv(csv_file)
    assert "reserved restkey name" in str(exc_info.value)


def test_empty_file_raises_csv_file_error(tmp_path):
    """Test that a 0-byte file raises CSVFileError."""
    csv_file = tmp_path / "empty.csv"
    csv_file.write_text("", encoding="utf-8")

    with pytest.raises(CSVFileError) as exc_info:
        load_and_validate_csv(csv_file)
    assert "empty" in str(exc_info.value).lower()


def test_header_only_file_returns_empty_results(tmp_path):
    """Test that a CSV with headers but no transaction rows returns empty accepted and rejected lists."""
    csv_file = tmp_path / "header_only.csv"
    csv_file.write_text("Date,Description,Amount,Type\n", encoding="utf-8")

    accepted, rejected = load_and_validate_csv(csv_file)

    assert accepted == []
    assert rejected == []


def test_missing_file_raises_file_not_found(tmp_path):
    """Test that a non-existent file path raises FileNotFoundError (and CSVFileError)."""
    non_existent = tmp_path / "does_not_exist_12345.csv"

    with pytest.raises(FileNotFoundError):
        load_and_validate_csv(non_existent)

    with pytest.raises(CSVFileError):
        load_and_validate_csv(non_existent)


def test_extra_row_field_rejected(tmp_path):
    """Test that a row containing extra values beyond the header is rejected."""
    csv_file = tmp_path / "extra_fields.csv"
    csv_file.write_text(
        "Date,Description,Amount,Type\n"
        "2026-10-01,Groceries,10.50,DEBIT,EXTRA_UNWANTED_VALUE\n",
        encoding="utf-8",
    )

    accepted, rejected = load_and_validate_csv(csv_file)

    assert len(accepted) == 0
    assert len(rejected) == 1
    assert rejected[0]["record_number"] == 2
    assert "extra columns" in rejected[0]["reason"].lower()


def test_missing_row_field_rejected(tmp_path):
    """Test that a row missing a field (too few columns) is rejected."""
    csv_file = tmp_path / "missing_fields.csv"
    csv_file.write_text(
        "Date,Description,Amount,Type\n"
        "2026-10-01,Groceries,10.50\n",
        encoding="utf-8",
    )

    accepted, rejected = load_and_validate_csv(csv_file)

    assert len(accepted) == 0
    assert len(rejected) == 1
    assert rejected[0]["record_number"] == 2
    assert "missing columns" in rejected[0]["reason"].lower()


def test_malformed_csv_quoting_raises_csv_file_error(tmp_path):
    """
    Test that malformed CSV quoting (syntax error) raises CSVFileError and causes
    the entire import attempt to fail, even when a valid row precedes the malformed row.
    """
    csv_file = tmp_path / "malformed_quotes.csv"
    csv_file.write_text(
        'Date,Description,Amount,Type\n'
        '2026-10-01,Valid Store Before Error,10.00,DEBIT\n'
        '2026-10-02,"DMART"STORE,20.00,DEBIT\n',
        encoding="utf-8",
    )

    with pytest.raises(CSVFileError) as exc_info:
        load_and_validate_csv(csv_file)

    assert "Malformed CSV parser failure" in str(exc_info.value)
    # Confirm the original csv.Error exception is preserved as __cause__
    assert exc_info.value.__cause__ is not None


def test_malformed_csv_header_quoting_raises_csv_file_error(tmp_path):
    """Test that malformed CSV quoting in the header row itself raises CSVFileError."""
    csv_file = tmp_path / "malformed_header_quotes.csv"
    csv_file.write_text(
        'Date,"Description"Junk,Amount,Type\n'
        '2026-10-01,Groceries,10.00,DEBIT\n',
        encoding="utf-8",
    )

    with pytest.raises(CSVFileError) as exc_info:
        load_and_validate_csv(csv_file)

    assert "Malformed CSV parser failure" in str(exc_info.value)
    assert exc_info.value.__cause__ is not None


# ============================================================================
# Section C: Transaction Field Validation
# ============================================================================

def test_validate_date_valid():
    """Test valid calendar dates in YYYY-MM-DD format."""
    assert validate_date("2026-10-03") == "2026-10-03"
    assert validate_date("2024-02-29") == "2024-02-29"  # leap year
    assert validate_date(" 2026-01-01 ") == "2026-01-01"


def test_validate_date_invalid():
    """Test invalid dates: non-leap year, invalid month/day, wrong formats."""
    invalid_dates = [
        "2026-02-29",  # 2026 is not a leap year
        "2026-13-01",  # month 13
        "2026-00-01",  # month 00
        "2026-10-32",  # day 32
        "26-10-03",    # 2-digit year
        "2026/10/03",  # slashes
        "2026-10-3",   # single digit day
        "20261003",    # no hyphens
        "not-a-date",  # random string
        "",            # empty
        "   ",         # whitespace only
    ]
    for d in invalid_dates:
        with pytest.raises(ValueError):
            validate_date(d)


def test_validate_description_valid():
    """Test valid descriptions preserve original text."""
    assert validate_description("DMART STORE 018") == "DMART STORE 018"
    assert validate_description("  Coffee Shop  ") == "  Coffee Shop  "


def test_validate_description_empty():
    """Test empty or whitespace-only descriptions are rejected."""
    for empty_desc in ["", "   ", "\t", "\n"]:
        with pytest.raises(ValueError) as exc_info:
            validate_description(empty_desc)
        assert "empty description" in str(exc_info.value).lower()


def test_validate_type_normalization():
    """Test that type accepts DEBIT and CREDIT with case/whitespace normalization."""
    assert validate_type("DEBIT") == "DEBIT"
    assert validate_type("debit") == "DEBIT"
    assert validate_type(" debit ") == "DEBIT"
    assert validate_type("CREDIT") == "CREDIT"
    assert validate_type("credit") == "CREDIT"
    assert validate_type(" Credit ") == "CREDIT"


def test_validate_type_invalid():
    """Test invalid types are rejected with standard reason."""
    for bad_type in ["TRANSFER", "REFUND", "INCOME", "UNKNOWN", "", "123"]:
        with pytest.raises(ValueError) as exc_info:
            validate_type(bad_type)
        assert "Type must be DEBIT or CREDIT" in str(exc_info.value)


# ============================================================================
# Section D: Monetary Conversion (to_paise)
# ============================================================================

def test_to_paise_exact_values():
    """Test valid positive amounts convert to exact integer paise."""
    assert to_paise("10.50") == 1050
    assert to_paise("12.340") == 1234  # normalized 2-decimal representation
    assert to_paise("12") == 1200
    assert to_paise("12.3") == 1230
    assert to_paise("0.01") == 1
    assert to_paise("100.00") == 10000
    assert to_paise(" 10.50 ") == 1050


def test_to_paise_rejects_three_decimal_places():
    """Test that values with > 2 decimal places are rejected without silent rounding."""
    with pytest.raises(ValueError) as exc_info:
        to_paise("12.345")
    assert "amount has more than two decimal places" in str(exc_info.value)

    with pytest.raises(ValueError):
        to_paise("0.001")


def test_to_paise_rejects_zero_and_negative():
    """Test zero and negative amounts are rejected."""
    for bad_amount in ["0", "0.00", "-0.01", "-1.00", "-125.50"]:
        with pytest.raises(ValueError) as exc_info:
            to_paise(bad_amount)
        assert "amount must be positive" in str(exc_info.value)


def test_to_paise_rejects_non_finite():
    """Test NaN and positive/negative infinity are rejected."""
    for non_finite in ["NaN", "nan", "Infinity", "-Infinity", "+Infinity", "inf", "-inf"]:
        with pytest.raises(ValueError) as exc_info:
            to_paise(non_finite)
        assert "finite" in str(exc_info.value).lower()


def test_to_paise_rejects_scientific_notation():
    """Test scientific notation is explicitly rejected for monetary values."""
    for sci in ["1e2", "1e-5", "1.5E3"]:
        with pytest.raises(ValueError) as exc_info:
            to_paise(sci)
        assert "scientific notation" in str(exc_info.value).lower()


def test_to_paise_rejects_invalid_numeric_text():
    """Test letters, multiple decimal points, currency symbols, and commas are rejected."""
    for invalid in ["abc", "12.34.56", "", "   ", "₹12.50", "1,234.50", "$10"]:
        with pytest.raises(ValueError):
            to_paise(invalid)


def test_to_paise_extreme_precision_regression():
    """
    Phase 8 Regression Test (Defect 1):
    Ensure amounts with digits beyond 2 decimal places are strictly rejected,
    even when length exceeds Python's default Decimal context precision (28 digits).
    Ensure trailing zeroes beyond 2 places are accepted according to exact representability.
    """
    # 1. Extreme fractional digit beyond 28-digit precision must be rejected
    with pytest.raises(ValueError, match="amount has more than two decimal places"):
        to_paise("10.000000000000000000000000001")

    # 2. Standard 3-decimal fraction must be rejected
    with pytest.raises(ValueError, match="amount has more than two decimal places"):
        to_paise("12.345")

    # 3. Exactly representable 2-decimal amounts with trailing zeroes must be accepted
    assert to_paise("12.340") == 1234
    assert to_paise("12.340000000000000000000000000") == 1234
    assert to_paise("10.500000000000000000000000000") == 1050

    # 4. Tiny sub-paise fraction must be rejected
    with pytest.raises(ValueError, match="amount has more than two decimal places"):
        to_paise("0.0000000000000000000000000000001")


def test_to_paise_maximum_integer_bounds():
    """
    Phase 8 Regression Test:
    Verify that amounts up to SQLite's signed 64-bit integer limit (9223372036854775807 paise)
    are accepted, while amounts exceeding that boundary are cleanly rejected.
    """
    # Maximum positive 64-bit integer in paise (₹92,233,720,368,547,758.07)
    max_amount_str = "92233720368547758.07"
    assert to_paise(max_amount_str) == MAX_PAISE_INTEGER

    # Exceeding the maximum 64-bit integer by 1 paise (₹92,233,720,368,547,758.08)
    overflow_amount_str = "92233720368547758.08"
    with pytest.raises(ValueError, match="amount exceeds maximum supported value"):
        to_paise(overflow_amount_str)

    # Astronomical amount from Phase 7 audit reproduction
    with pytest.raises(ValueError, match="amount exceeds maximum supported value"):
        to_paise("10000000000000000000.00")


# ============================================================================
# Section E: Error Isolation & Surrounding Rows
# ============================================================================

def test_row_isolation_valid_around_invalid(tmp_path):
    """
    CRITICAL SAFETY REQUIREMENT:
    Test that invalid rows (bad date, bad amount, missing columns, extra columns)
    do not corrupt or discard valid neighboring rows.
    """
    csv_file = tmp_path / "mixed_valid_invalid.csv"
    csv_file.write_text(
        "Date,Description,Amount,Type\n"
        "2026-10-01,Valid Before 1,10.00,DEBIT\n"              # Row 2: VALID
        "2026-02-29,Bad Date Non Leap,20.00,DEBIT\n"          # Row 3: INVALID date
        "2026-10-02,Valid Between 1 and 2,30.00,CREDIT\n"      # Row 4: VALID
        "2026-10-03,Bad Amount Three Decimals,12.345,DEBIT\n"  # Row 5: INVALID amount
        "2026-10-04,Valid Between 2 and 3,40.00,DEBIT\n"       # Row 6: VALID
        "2026-10-05,Missing Column,50.00\n"                    # Row 7: INVALID missing field
        "2026-10-06,Valid Between 3 and 4,60.00,CREDIT\n"      # Row 8: VALID
        "2026-10-07,Extra Column,70.00,DEBIT,EXTRA\n"          # Row 9: INVALID extra field
        "2026-10-08,Bad Type,80.00,TRANSFER\n"                 # Row 10: INVALID type
        "2026-10-09,Valid After Final,90.00,DEBIT\n",          # Row 11: VALID
        encoding="utf-8",
    )

    accepted, rejected = load_and_validate_csv(csv_file)

    # 5 valid rows accepted
    assert len(accepted) == 5
    assert [r["description"] for r in accepted] == [
        "Valid Before 1",
        "Valid Between 1 and 2",
        "Valid Between 2 and 3",
        "Valid Between 3 and 4",
        "Valid After Final",
    ]
    assert [r["amount_paise"] for r in accepted] == [1000, 3000, 4000, 6000, 9000]

    # 5 invalid rows rejected with exact record numbers
    assert len(rejected) == 5
    assert [r["record_number"] for r in rejected] == [3, 5, 7, 9, 10]
    assert "invalid date" in rejected[0]["reason"].lower()
    assert "amount has more than two decimal places" in rejected[1]["reason"].lower()
    assert "missing columns" in rejected[2]["reason"].lower()
    assert "extra columns" in rejected[3]["reason"].lower()
    assert "Type must be DEBIT or CREDIT" in rejected[4]["reason"]


def test_stream_input_support():
    """Test that load_and_validate_csv also supports in-memory StringIO streams."""
    stream = io.StringIO(
        "Date,Description,Amount,Type\n"
        "2026-10-01,Streaming Store,25.00,DEBIT\n"
    )

    accepted, rejected = load_and_validate_csv(stream)

    assert len(accepted) == 1
    assert len(rejected) == 0
    assert accepted[0]["description"] == "Streaming Store"
    assert accepted[0]["amount_paise"] == 2500


def test_invalid_utf8_file_raises_csv_file_error(tmp_path):
    """Test that a file containing invalid UTF-8 byte sequences raises CSVFileError."""
    bad_file = tmp_path / "invalid_utf8.csv"
    bad_file.write_bytes(b"\xff\xfe\x00\x00Invalid UTF-8 bytes")

    with pytest.raises(CSVFileError) as exc_info:
        load_and_validate_csv(bad_file)

    assert "cannot read csv file" in str(exc_info.value).lower()
    assert isinstance(exc_info.value.__cause__, UnicodeDecodeError)


def test_invalid_utf8_stream_raises_csv_file_error():
    """Test that a stream that raises UnicodeDecodeError during read is converted to CSVFileError."""
    raw_bytes = io.BytesIO(b"\xff\xfe\x00\x00Invalid UTF-8 stream")
    stream = io.TextIOWrapper(raw_bytes, encoding="utf-8")

    with pytest.raises(CSVFileError) as exc_info:
        load_and_validate_csv(stream)

    assert "cannot read csv stream" in str(exc_info.value).lower()
    assert isinstance(exc_info.value.__cause__, UnicodeDecodeError)
