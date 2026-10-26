"""
SpendSense — Milestone 5 Tests: CLI End-to-End Integration.

Covers:
1. Successful end-to-end import with expected summary output and database replacement.
2. Correct accepted and rejected counts when valid and invalid rows coexist.
3. Correct display of integer-paise amounts as rupees (e.g., 1050 -> '₹10.50', 0 -> '₹0.00').
4. Successful re-import replaces rather than appends records.
5. Duplicate-looking valid input rows are both retained.
6. Missing input file preserves an existing database and returns non-zero exit code.
7. Structurally invalid CSV preserves an existing database and returns non-zero exit code.
8. All-invalid CSV preserves an existing database and returns non-zero exit code.
9. Failed database replacement preserves the existing database and surfaces an error.
10. Credits, refunds, and transfers remain distinct in the printed report.
11. Potential-outlier and not-evaluated results are displayed accurately with non-fraud wording.
12. Dataset with no outliers or empty results runs without crashing.
13. Subprocess execution of the real CLI entry point (python main.py).
"""

from pathlib import Path
import subprocess
import sys
import pytest

from main import format_paise_to_inr, format_report, main, run_pipeline
from storage import get_connection, replace_transactions


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Fixture providing a temporary database file path."""
    return tmp_path / "test_spendsense_m5.db"


@pytest.fixture
def valid_csv_path(tmp_path: Path) -> Path:
    """
    Fixture providing a valid synthetic CSV file:
    - 5 Dining DEBIT transactions (median=2500, MAD=500, 1 outlier of 35000 paise)
    - 1 Groceries DEBIT: 4500 paise
    - 1 Transfer DEBIT: 10000 paise (excluded from expenses)
    - 1 Income CREDIT: 500000 paise
    - 1 Refund CREDIT: 1200 paise (not netted)
    - 1 Transfer CREDIT: 25000 paise
    """
    csv_file = tmp_path / "valid_sample.csv"
    content = (
        "Date,Description,Amount,Type\n"
        "2026-10-01,DINING MEAL 1,20.00,DEBIT\n"
        "2026-10-02,DINING MEAL 2,25.00,DEBIT\n"
        "2026-10-03,DINING MEAL 3,25.00,DEBIT\n"
        "2026-10-04,DINING MEAL 4,30.00,DEBIT\n"
        "2026-10-05,DINING MEAL LUXURY,350.00,DEBIT\n"
        "2026-10-06,BIGBASKET GROCERIES,45.00,DEBIT\n"
        "2026-10-07,TRANSFER TO SAVINGS,100.00,DEBIT\n"
        "2026-10-08,MONTHLY SALARY,5000.00,CREDIT\n"
        "2026-10-09,MERCHANT REFUND,12.00,CREDIT\n"
        "2026-10-10,INCOMING TRANSFER,250.00,CREDIT\n"
    )
    csv_file.write_text(content, encoding="utf-8")
    return csv_file


# ============================================================================
# Section 1: Money Formatting Unit Tests
# ============================================================================

def test_format_paise_to_inr():
    """Verify format_paise_to_inr formats integer paise to INR rupees without float conversion."""
    assert format_paise_to_inr(0) == "₹0.00"
    assert format_paise_to_inr(5) == "₹0.05"
    assert format_paise_to_inr(50) == "₹0.50"
    assert format_paise_to_inr(100) == "₹1.00"
    assert format_paise_to_inr(1050) == "₹10.50"
    assert format_paise_to_inr(4500) == "₹45.00"
    assert format_paise_to_inr(500000) == "₹5000.00"
    assert format_paise_to_inr(-1050) == "-₹10.50"

    # Type validation
    with pytest.raises(TypeError):
        format_paise_to_inr(10.50)  # float forbidden!
    with pytest.raises(TypeError):
        format_paise_to_inr("1050")
    with pytest.raises(TypeError):
        format_paise_to_inr(True)  # bool forbidden!


# ============================================================================
# Section 2: End-to-End Pipeline & Integration Tests
# ============================================================================

def test_pipeline_successful_run(valid_csv_path, db_path, capsys):
    """Test full pipeline execution with valid CSV produces exit code 0 and populated database."""
    exit_code = run_pipeline(csv_path=valid_csv_path, db_path=db_path)
    assert exit_code == 0

    out = capsys.readouterr().out
    assert "SPENDSENSE — TRANSACTION & ANOMALY REPORT" in out
    assert "Import:     SUCCESS (10 accepted, 0 rejected)" in out
    assert "Total Expenses: ₹495.00" in out  # 20+25+25+30+350 + 45 = 495.00
    assert "Total Credits: ₹5262.00" in out   # 5000 + 12 + 250 = 5262.00
    assert "Total Transfers: ₹350.00" in out  # 100 + 250 = 350.00
    assert "DINING MEAL LUXURY" in out
    assert "Modified Z-Score: 43.84" in out
    assert "potential outlier" in out.lower()
    assert "fraud" not in out.lower()

    # Verify database contents
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS cnt FROM transactions;")
        assert cur.fetchone()["cnt"] == 10
    finally:
        conn.close()


def test_pipeline_coexisting_valid_and_invalid_rows(tmp_path, db_path, capsys):
    """
    When valid and invalid rows coexist:
    - Accepted rows are imported.
    - Rejected rows are reported with record and line numbers.
    - Exit code is 0.
    """
    mixed_csv = tmp_path / "mixed.csv"
    mixed_csv.write_text(
        "Date,Description,Amount,Type\n"
        "2026-10-01,VALID DINING,25.00,DEBIT\n"
        "2026-02-30,BAD DATE,10.00,DEBIT\n"
        "2026-10-02,NEGATIVE AMOUNT,-50.00,DEBIT\n"
        "2026-10-03,VALID GROCERY,100.00,DEBIT\n",
        encoding="utf-8",
    )

    exit_code = run_pipeline(csv_path=mixed_csv, db_path=db_path)
    assert exit_code == 0

    out = capsys.readouterr().out
    assert "Total rows considered: 4" in out
    assert "Accepted records:      2" in out
    assert "Rejected rows:         2" in out
    assert "Record 3 (Line 3):" in out
    assert "Record 4 (Line 4):" in out

    # Verify database contains exactly the 2 valid records
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS cnt FROM transactions;")
        assert cur.fetchone()["cnt"] == 2
    finally:
        conn.close()


def test_pipeline_reimport_replaces_rather_than_appends(tmp_path, db_path):
    """Re-importing a new CSV replaces all prior records in SQLite; no duplicate appends."""
    csv_1 = tmp_path / "batch1.csv"
    csv_1.write_text(
        "Date,Description,Amount,Type\n"
        "2026-10-01,FIRST BATCH A,10.00,DEBIT\n"
        "2026-10-02,FIRST BATCH B,20.00,DEBIT\n",
        encoding="utf-8",
    )
    assert run_pipeline(csv_path=csv_1, db_path=db_path) == 0

    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS cnt FROM transactions;")
        assert cur.fetchone()["cnt"] == 2
    finally:
        conn.close()

    # Second batch with 3 different records
    csv_2 = tmp_path / "batch2.csv"
    csv_2.write_text(
        "Date,Description,Amount,Type\n"
        "2026-10-10,SECOND BATCH X,30.00,DEBIT\n"
        "2026-10-11,SECOND BATCH Y,40.00,DEBIT\n"
        "2026-10-12,SECOND BATCH Z,50.00,DEBIT\n",
        encoding="utf-8",
    )
    assert run_pipeline(csv_path=csv_2, db_path=db_path) == 0

    # Total must be 3, NOT 5 (2 + 3)
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT description FROM transactions ORDER BY id ASC;")
        rows = [r["description"] for r in cur.fetchall()]
        assert len(rows) == 3
        assert rows == ["SECOND BATCH X", "SECOND BATCH Y", "SECOND BATCH Z"]
    finally:
        conn.close()


def test_pipeline_duplicate_looking_rows_retained(tmp_path, db_path):
    """Identical-looking valid rows within one input file are both retained (no accidental deduplication)."""
    dup_csv = tmp_path / "duplicates.csv"
    dup_csv.write_text(
        "Date,Description,Amount,Type\n"
        "2026-10-01,SWIGGY ORDER,30.00,DEBIT\n"
        "2026-10-01,SWIGGY ORDER,30.00,DEBIT\n",
        encoding="utf-8",
    )
    assert run_pipeline(csv_path=dup_csv, db_path=db_path) == 0

    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS cnt FROM transactions;")
        assert cur.fetchone()["cnt"] == 2
    finally:
        conn.close()


# ============================================================================
# Section 3: Database Preservation on Failures
# ============================================================================

def test_pipeline_missing_file_preserves_database(tmp_path, db_path, capsys):
    """A missing input file returns exit code 1 and preserves any existing database dataset."""
    # Seed prior database with 1 valid row
    prior_records = [{
        "transaction_date": "2026-09-01",
        "description": "PRIOR EXPENSE",
        "normalized_description": "prior expense",
        "transaction_type": "DEBIT",
        "amount_paise": 5000,
        "category": "Dining",
        "rule_id": "R_DINING",
    }]
    replace_transactions(db_path, prior_records)

    missing_csv = tmp_path / "does_not_exist.csv"
    exit_code = run_pipeline(csv_path=missing_csv, db_path=db_path)
    assert exit_code == 1

    err = capsys.readouterr().err
    assert "Error:" in err
    assert "CSV file not found" in err

    # Confirm database was untouched
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT description FROM transactions;")
        rows = [r["description"] for r in cur.fetchall()]
        assert rows == ["PRIOR EXPENSE"]
    finally:
        conn.close()


def test_pipeline_structurally_invalid_csv_preserves_database(tmp_path, db_path, capsys):
    """A structurally invalid CSV (e.g. wrong headers) preserves existing database."""
    prior_records = [{
        "transaction_date": "2026-09-01",
        "description": "PRIOR EXPENSE",
        "normalized_description": "prior expense",
        "transaction_type": "DEBIT",
        "amount_paise": 5000,
        "category": "Dining",
        "rule_id": "R_DINING",
    }]
    replace_transactions(db_path, prior_records)

    bad_csv = tmp_path / "bad_header.csv"
    bad_csv.write_text("Date,WrongCol,Amount,Type\n2026-10-01,test,10.00,DEBIT\n", encoding="utf-8")

    exit_code = run_pipeline(csv_path=bad_csv, db_path=db_path)
    assert exit_code == 1

    err = capsys.readouterr().err
    assert "Invalid CSV file" in err

    # Database still intact
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT description FROM transactions;")
        assert cur.fetchone()["description"] == "PRIOR EXPENSE"
    finally:
        conn.close()


def test_pipeline_all_invalid_csv_preserves_database(tmp_path, db_path, capsys):
    """A CSV with headers but only invalid rows preserves existing database."""
    prior_records = [{
        "transaction_date": "2026-09-01",
        "description": "PRIOR EXPENSE",
        "normalized_description": "prior expense",
        "transaction_type": "DEBIT",
        "amount_paise": 5000,
        "category": "Dining",
        "rule_id": "R_DINING",
    }]
    replace_transactions(db_path, prior_records)

    all_bad_csv = tmp_path / "all_bad.csv"
    all_bad_csv.write_text(
        "Date,Description,Amount,Type\n"
        "invalid_date,Desc,10.00,DEBIT\n"
        "2026-10-01,,10.00,DEBIT\n"
        "2026-10-01,Desc,-5.00,DEBIT\n",
        encoding="utf-8",
    )

    exit_code = run_pipeline(csv_path=all_bad_csv, db_path=db_path)
    assert exit_code == 1

    err = capsys.readouterr().err
    assert "No valid records found" in err
    assert "Prior database preserved" in err

    # Database still intact
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT description FROM transactions;")
        assert cur.fetchone()["description"] == "PRIOR EXPENSE"
    finally:
        conn.close()


def test_pipeline_empty_csv_file_preserves_database(tmp_path, db_path, capsys):
    """An empty 0-byte CSV preserves existing database."""
    prior_records = [{
        "transaction_date": "2026-09-01",
        "description": "PRIOR EXPENSE",
        "normalized_description": "prior expense",
        "transaction_type": "DEBIT",
        "amount_paise": 5000,
        "category": "Dining",
        "rule_id": "R_DINING",
    }]
    replace_transactions(db_path, prior_records)

    empty_csv = tmp_path / "empty.csv"
    empty_csv.write_text("", encoding="utf-8")

    exit_code = run_pipeline(csv_path=empty_csv, db_path=db_path)
    assert exit_code == 1

    err = capsys.readouterr().err
    assert "Invalid CSV file" in err

    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT description FROM transactions;")
        assert cur.fetchone()["description"] == "PRIOR EXPENSE"
    finally:
        conn.close()


# ============================================================================
# Section 4: CLI Argument Parsing and Subprocess Invocations
# ============================================================================

def test_main_cli_missing_arguments(capsys):
    """Calling main without arguments returns code 2 (usage error)."""
    exit_code = main([])
    assert exit_code == 2


def test_main_cli_help(capsys):
    """Calling main with --help returns code 0."""
    exit_code = main(["--help"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "SpendSense" in out
    assert "--db" in out


def test_main_cli_with_valid_args(valid_csv_path, db_path):
    """Calling main with explicit csv and --db paths returns code 0."""
    exit_code = main([str(valid_csv_path), "--db", str(db_path)])
    assert exit_code == 0

    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS cnt FROM transactions;")
        assert cur.fetchone()["cnt"] == 10
    finally:
        conn.close()


def test_real_subprocess_cli_invocation(valid_csv_path, db_path):
    """Invoke the real CLI via python main.py in a subprocess."""
    import os
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    result = subprocess.run(
        [sys.executable, "main.py", str(valid_csv_path), "--db", str(db_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    assert result.returncode == 0
    assert "SPENDSENSE — TRANSACTION & ANOMALY REPORT" in result.stdout
    assert "Total Expenses: ₹495.00" in result.stdout
    assert "Total Credits: ₹5262.00" in result.stdout
    assert "Total Transfers: ₹350.00" in result.stdout
    assert "DINING MEAL LUXURY" in result.stdout


def test_real_subprocess_cli_failure_path_preserves_db(tmp_path, db_path):
    """Demonstrate via subprocess that invalid input preserves prior valid database."""
    import os
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    # First: seed database via real subprocess
    valid_csv = tmp_path / "valid_seed.csv"
    valid_csv.write_text(
        "Date,Description,Amount,Type\n"
        "2026-10-01,SEED MEAL,25.00,DEBIT\n",
        encoding="utf-8",
    )
    res1 = subprocess.run(
        [sys.executable, "main.py", str(valid_csv), "--db", str(db_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    assert res1.returncode == 0

    # Second: run failure path with missing file
    res2 = subprocess.run(
        [sys.executable, "main.py", str(tmp_path / "nonexistent.csv"), "--db", str(db_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    assert res2.returncode == 1
    assert "CSV file not found" in res2.stderr

    # Third: check database still has SEED MEAL
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT description FROM transactions;")
        rows = [r["description"] for r in cur.fetchall()]
        assert rows == ["SEED MEAL"]
    finally:
        conn.close()


def test_pipeline_invalid_utf8_file_preserves_database(tmp_path, db_path, capsys):
    """Test that pipeline execution on invalid UTF-8 CSV exits with code 1, clean error, and preserves DB."""
    # Seed database
    prior_records = [{
        "transaction_date": "2026-09-01",
        "description": "PRIOR RECORD",
        "normalized_description": "prior record",
        "transaction_type": "DEBIT",
        "amount_paise": 5000,
        "category": "Dining",
        "rule_id": "R_DINING",
    }]
    replace_transactions(db_path, prior_records)

    bad_csv = tmp_path / "invalid_utf8.csv"
    bad_csv.write_bytes(b"\xff\xfe\x00\x00Corrupt UTF-8 bytes")

    exit_code = run_pipeline(csv_path=bad_csv, db_path=db_path)
    assert exit_code == 1

    err = capsys.readouterr().err
    assert err.startswith("Error: Invalid CSV file:")
    assert "Traceback" not in err

    # Verify prior dataset is untouched
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT description FROM transactions;")
        assert cur.fetchone()["description"] == "PRIOR RECORD"
    finally:
        conn.close()


def test_real_subprocess_cli_invalid_utf8_preserves_database(tmp_path, db_path):
    """Demonstrate via subprocess that invalid UTF-8 CSV prints clean error and preserves database."""
    import os
    env = dict(os.environ, PYTHONIOENCODING="utf-8")

    # Seed database
    valid_csv = tmp_path / "valid_seed.csv"
    valid_csv.write_text("Date,Description,Amount,Type\n2026-10-01,SEED MEAL,25.00,DEBIT\n", encoding="utf-8")
    res1 = subprocess.run(
        [sys.executable, "main.py", str(valid_csv), "--db", str(db_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    assert res1.returncode == 0

    # Run invalid UTF-8 file through CLI
    bad_csv = tmp_path / "bad_bytes.csv"
    bad_csv.write_bytes(b"\xff\xfe\x00\x00Corrupt UTF-8 bytes")

    res2 = subprocess.run(
        [sys.executable, "main.py", str(bad_csv), "--db", str(db_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    assert res2.returncode == 1
    assert res2.stderr.startswith("Error: Invalid CSV file:")
    assert "Traceback" not in res2.stderr
    assert res2.stdout == ""

    # Verify database still contains seed record
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT description FROM transactions;")
        rows = [r["description"] for r in cur.fetchall()]
        assert rows == ["SEED MEAL"]
    finally:
        conn.close()


def test_bundled_sample_transactions_csv(tmp_path, capsys):
    """Verify that the bundled sample_transactions.csv imports cleanly and matches expected figures."""
    sample_csv = Path("data") / "sample_transactions.csv"
    assert sample_csv.exists()

    db_path = tmp_path / "test_sample_bundled.db"
    exit_code = run_pipeline(csv_path=sample_csv, db_path=db_path)
    assert exit_code == 0

    out = capsys.readouterr().out
    assert "Import:     SUCCESS (16 accepted, 0 rejected)" in out
    assert "Total Expenses: ₹10739.50" in out
    assert "Total Credits: ₹85500.00" in out
    assert "Total Transfers: ₹25000.00" in out
    assert "Swiggy Feast" in out
    assert "Modified Z-Score: 52.61" in out


def test_cli_oversized_amount_preserves_database(tmp_path):
    """
    Phase 8 Regression Test (Defect 2):
    Verify that an import with an amount exceeding SQLite's 64-bit integer limit
    exits with non-zero code, displays a clean readable error without an unhandled traceback,
    and preserves the existing database contents intact.
    """
    db_path = tmp_path / "test_overflow_preserve.db"

    # 1. Seed database with an initial record
    seed_csv = tmp_path / "seed.csv"
    seed_csv.write_text(
        "Date,Description,Amount,Type\n"
        "2026-10-01,INITIAL SEED RECORD,100.00,DEBIT\n",
        encoding="utf-8",
    )
    res_seed = subprocess.run(
        [sys.executable, "main.py", str(seed_csv), "--db", str(db_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert res_seed.returncode == 0

    # Verify seed record in DB
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT description FROM transactions;")
        rows = [r["description"] for r in cur.fetchall()]
        assert rows == ["INITIAL SEED RECORD"]
    finally:
        conn.close()

    # 2. Run CSV containing an oversized amount (Phase 7 audit reproduction)
    overflow_csv = tmp_path / "overflow.csv"
    overflow_csv.write_text(
        "Date,Description,Amount,Type\n"
        "2026-03-01,Big Money,10000000000000000000.00,DEBIT\n",
        encoding="utf-8",
    )
    res = subprocess.run(
        [sys.executable, "main.py", str(overflow_csv), "--db", str(db_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    # Must exit nonzero without traceback
    assert res.returncode == 1
    assert "Traceback" not in res.stderr
    assert "amount exceeds maximum supported value" in res.stderr
    assert "Prior database preserved" in res.stderr

    # 3. Verify prior database remains completely intact
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT description, amount_paise FROM transactions;")
        rows = [(r["description"], r["amount_paise"]) for r in cur.fetchall()]
        assert rows == [("INITIAL SEED RECORD", 10000)]
    finally:
        conn.close()
