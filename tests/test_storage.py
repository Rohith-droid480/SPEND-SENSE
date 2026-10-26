"""
SpendSense — Milestone 3 Tests: SQLite Storage & Atomic Replacement.

Covers:
1. Database initialization and exact schema structure (columns, types, constraints, no extra tables).
2. Inserting valid records and reading them back with exact field persistence.
3. Successful re-import replacement semantics (replaces old dataset; does NOT append).
4. Duplicate-looking rows within a single input batch are both retained with distinct primary keys.
5. Empty input rejection: preserves existing dataset without deletion.
6. Invalid record pre-validation rejection: preserves existing dataset.
7. Mid-insertion failure rollback: preserves previous committed dataset.
8. Parameterized SQL verification (injection safety with quotes, semicolons, SQL commands).
9. Connection cleanup on success and error.
"""

from pathlib import Path
import sqlite3
import pytest

from storage import (
    MAX_SQLITE_INTEGER,
    TABLE_NAME,
    get_connection,
    initialize_database,
    read_transactions,
    replace_transactions,
    validate_record_for_storage,
)


@pytest.fixture
def db_path(tmp_path) -> Path:
    """Fixture providing a temporary database file path."""
    return tmp_path / "test_spendsense.db"


@pytest.fixture
def sample_valid_records() -> list[dict]:
    """Fixture providing a standard list of validated and categorized records."""
    return [
        {
            "transaction_date": "2026-10-01",
            "description": "DMART STORE 018",
            "normalized_description": "dmart store 018",
            "transaction_type": "DEBIT",
            "amount_paise": 12550,
            "category": "Groceries",
            "rule_id": "R_GROCERIES",
        },
        {
            "transaction_date": "2026-10-02",
            "description": "MONTHLY SALARY",
            "normalized_description": "monthly salary",
            "transaction_type": "CREDIT",
            "amount_paise": 5000000,
            "category": "Income",
            "rule_id": "R_INCOME",
        },
        {
            "transaction_date": "2026-10-03",
            "description": "UBER EATS ORDER",
            "normalized_description": "uber eats order",
            "transaction_type": "DEBIT",
            "amount_paise": 45000,
            "category": "Dining",
            "rule_id": "R_DINING",
        },
    ]


# ============================================================================
# Section 1: Schema and Initialization Tests
# ============================================================================

def test_initialize_database_creates_exact_schema(db_path):
    """Test that initialize_database creates the exact table and columns."""
    initialize_database(db_path)

    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        # Verify table exists
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (TABLE_NAME,))
        assert cur.fetchone() is not None

        # Verify only one application table exists
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [row[0] for row in cur.fetchall()]
        assert tables == ["transactions"]

        # Inspect table columns
        cur.execute("PRAGMA table_info(transactions);")
        columns = {row[1]: {"type": row[2].upper(), "notnull": row[3], "pk": row[5]} for row in cur.fetchall()}

        expected_columns = {
            "id": {"type": "INTEGER", "notnull": 0, "pk": 1},
            "transaction_date": {"type": "TEXT", "notnull": 1, "pk": 0},
            "description": {"type": "TEXT", "notnull": 1, "pk": 0},
            "normalized_description": {"type": "TEXT", "notnull": 1, "pk": 0},
            "transaction_type": {"type": "TEXT", "notnull": 1, "pk": 0},
            "amount_paise": {"type": "INTEGER", "notnull": 1, "pk": 0},
            "category": {"type": "TEXT", "notnull": 1, "pk": 0},
            "rule_id": {"type": "TEXT", "notnull": 1, "pk": 0},
        }

        assert columns == expected_columns
    finally:
        conn.close()


def test_schema_constraints_enforced(db_path):
    """Test CHECK constraints on transaction_type and amount_paise."""
    initialize_database(db_path)
    conn = get_connection(db_path)
    try:
        # 1. Invalid transaction_type ('TRANSFER' is not allowed in CHECK constraint)
        with pytest.raises(sqlite3.IntegrityError):
            with conn:
                conn.execute(
                    """
                    INSERT INTO transactions (
                        transaction_date, description, normalized_description,
                        transaction_type, amount_paise, category, rule_id
                    ) VALUES ('2026-10-01', 'Test', 'test', 'TRANSFER', 1000, 'Transfer', 'R_TRANSFER');
                    """
                )

        # 2. Non-positive amount_paise (amount_paise <= 0 fails CHECK constraint)
        with pytest.raises(sqlite3.IntegrityError):
            with conn:
                conn.execute(
                    """
                    INSERT INTO transactions (
                        transaction_date, description, normalized_description,
                        transaction_type, amount_paise, category, rule_id
                    ) VALUES ('2026-10-01', 'Test', 'test', 'DEBIT', 0, 'Uncategorized', 'R_UNKNOWN_DEBIT');
                    """
                )

        with pytest.raises(sqlite3.IntegrityError):
            with conn:
                conn.execute(
                    """
                    INSERT INTO transactions (
                        transaction_date, description, normalized_description,
                        transaction_type, amount_paise, category, rule_id
                    ) VALUES ('2026-10-01', 'Test', 'test', 'DEBIT', -500, 'Uncategorized', 'R_UNKNOWN_DEBIT');
                    """
                )
    finally:
        conn.close()


# ============================================================================
# Section 2: Insert and Read Tests
# ============================================================================

def test_replace_and_read_transactions(db_path, sample_valid_records):
    """Test inserting valid records and reading them back with exact values."""
    count = replace_transactions(db_path, sample_valid_records)
    assert count == 3

    rows = read_transactions(db_path)
    assert len(rows) == 3

    # Check first record fields
    r0 = rows[0]
    assert r0["id"] == 1
    assert r0["transaction_date"] == "2026-10-01"
    assert r0["description"] == "DMART STORE 018"
    assert r0["normalized_description"] == "dmart store 018"
    assert r0["transaction_type"] == "DEBIT"
    assert r0["amount_paise"] == 12550
    assert isinstance(r0["amount_paise"], int)
    assert r0["category"] == "Groceries"
    assert r0["rule_id"] == "R_GROCERIES"


def test_read_transactions_empty_database(db_path):
    """Test read_transactions returns empty list when table exists but has no rows."""
    initialize_database(db_path)
    assert read_transactions(db_path) == []


def test_read_transactions_nonexistent_database(tmp_path):
    """Test read_transactions returns empty list when database file has no table."""
    non_existent = tmp_path / "nonexistent.db"
    assert read_transactions(non_existent) == []


# ============================================================================
# Section 3: Replacement Semantics (Replaces, Does Not Append)
# ============================================================================

def test_reimport_replaces_previous_dataset_without_appending(db_path, sample_valid_records):
    """Test that a second import completely replaces the first batch instead of appending."""
    # Batch 1: 3 records
    replace_transactions(db_path, sample_valid_records)
    assert len(read_transactions(db_path)) == 3

    # Batch 2: 2 completely different records
    batch_2 = [
        {
            "transaction_date": "2026-10-10",
            "description": "NETFLIX",
            "normalized_description": "netflix",
            "transaction_type": "DEBIT",
            "amount_paise": 64900,
            "category": "Subscriptions",
            "rule_id": "R_SUBSCRIPTION",
        },
        {
            "transaction_date": "2026-10-11",
            "description": "REFUND AMAZON",
            "normalized_description": "refund amazon",
            "transaction_type": "CREDIT",
            "amount_paise": 15000,
            "category": "Refund",
            "rule_id": "R_REFUND",
        },
    ]

    count2 = replace_transactions(db_path, batch_2)
    assert count2 == 2

    stored = read_transactions(db_path)
    # Must be 2 records, NOT 3 + 2 = 5 records!
    assert len(stored) == 2
    assert [r["description"] for r in stored] == ["NETFLIX", "REFUND AMAZON"]
    assert [r["amount_paise"] for r in stored] == [64900, 15000]


# ============================================================================
# Section 4: Duplicate-Looking Records Within One Batch
# ============================================================================

def test_duplicate_looking_records_in_same_csv_are_both_preserved(db_path):
    """
    Two legitimate transactions in the same CSV may have identical date, description,
    amount, and type. The database must preserve both records with distinct primary keys.
    """
    identical_records = [
        {
            "transaction_date": "2026-10-05",
            "description": "COFFEE SHOP",
            "normalized_description": "coffee shop",
            "transaction_type": "DEBIT",
            "amount_paise": 25000,
            "category": "Uncategorized",
            "rule_id": "R_UNKNOWN_DEBIT",
        },
        {
            "transaction_date": "2026-10-05",
            "description": "COFFEE SHOP",
            "normalized_description": "coffee shop",
            "transaction_type": "DEBIT",
            "amount_paise": 25000,
            "category": "Uncategorized",
            "rule_id": "R_UNKNOWN_DEBIT",
        },
    ]

    replace_transactions(db_path, identical_records)

    stored = read_transactions(db_path)
    assert len(stored) == 2
    assert stored[0]["id"] == 1
    assert stored[1]["id"] == 2
    assert stored[0]["description"] == stored[1]["description"]
    assert stored[0]["amount_paise"] == stored[1]["amount_paise"]


# ============================================================================
# Section 5: Data Preservation on Empty Input
# ============================================================================

def test_empty_input_preserves_existing_dataset(db_path, sample_valid_records):
    """Passing an empty records list must raise ValueError and leave existing data unchanged."""
    replace_transactions(db_path, sample_valid_records)
    initial_rows = read_transactions(db_path)
    assert len(initial_rows) == 3

    # Attempt replacement with empty list
    with pytest.raises(ValueError, match="empty"):
        replace_transactions(db_path, [])

    # Verify initial data remains intact
    after_attempt = read_transactions(db_path)
    assert after_attempt == initial_rows


def test_none_input_preserves_existing_dataset(db_path, sample_valid_records):
    """Passing None must raise ValueError and leave existing data unchanged."""
    replace_transactions(db_path, sample_valid_records)
    initial_rows = read_transactions(db_path)

    with pytest.raises(ValueError):
        replace_transactions(db_path, None)

    assert read_transactions(db_path) == initial_rows


# ============================================================================
# Section 6: Data Preservation on Invalid Record Input
# ============================================================================

def test_invalid_records_preserve_existing_dataset(db_path, sample_valid_records):
    """
    If any record in the batch fails pre-validation, the database must not be modified,
    and previous rows must remain completely intact.
    """
    replace_transactions(db_path, sample_valid_records)
    initial_rows = read_transactions(db_path)
    assert len(initial_rows) == 3

    invalid_batches = [
        # Missing required key
        [{"transaction_date": "2026-10-01", "description": "X"}],
        # Negative amount_paise
        [
            {
                "transaction_date": "2026-10-01",
                "description": "Bad Amount",
                "normalized_description": "bad amount",
                "transaction_type": "DEBIT",
                "amount_paise": -500,
                "category": "Uncategorized",
                "rule_id": "R_UNKNOWN_DEBIT",
            }
        ],
        # Zero amount_paise
        [
            {
                "transaction_date": "2026-10-01",
                "description": "Zero Amount",
                "normalized_description": "zero amount",
                "transaction_type": "DEBIT",
                "amount_paise": 0,
                "category": "Uncategorized",
                "rule_id": "R_UNKNOWN_DEBIT",
            }
        ],
        # Float amount_paise
        [
            {
                "transaction_date": "2026-10-01",
                "description": "Float Amount",
                "normalized_description": "float amount",
                "transaction_type": "DEBIT",
                "amount_paise": 10.50,
                "category": "Uncategorized",
                "rule_id": "R_UNKNOWN_DEBIT",
            }
        ],
        # Invalid transaction_type
        [
            {
                "transaction_date": "2026-10-01",
                "description": "Invalid Type",
                "normalized_description": "invalid type",
                "transaction_type": "TRANSFER",
                "amount_paise": 1000,
                "category": "Transfer",
                "rule_id": "R_TRANSFER",
            }
        ],
    ]

    for bad_batch in invalid_batches:
        with pytest.raises(ValueError):
            replace_transactions(db_path, bad_batch)
        # Verify previous records were NOT deleted
        assert read_transactions(db_path) == initial_rows


# ============================================================================
# Section 7: Mid-Insertion Failure Rollback
# ============================================================================

def test_insertion_failure_rolls_back_and_preserves_old_records(
    db_path, sample_valid_records
):
    """
    CRITICAL SAFETY REQUIREMENT:
    If a database-level error occurs during the executemany insertion step,
    the transaction must roll back, ensuring previous records are completely restored.

    We test this by installing an SQLite BEFORE INSERT trigger that aborts insertion.
    Because DELETE executes before INSERT in replace_transactions, this directly
    tests that SQLite transaction rollback restores deleted rows.
    """
    replace_transactions(db_path, sample_valid_records)
    initial_rows = read_transactions(db_path)
    assert len(initial_rows) == 3

    # Install an SQLite trigger that aborts any INSERT on the transactions table
    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                CREATE TRIGGER abort_insert_trigger
                BEFORE INSERT ON transactions
                BEGIN
                    SELECT RAISE(ABORT, 'Simulated database abort during insertion');
                END;
                """
            )
    finally:
        conn.close()

    new_batch = [
        {
            "transaction_date": "2026-10-20",
            "description": "SHOULD BE ROLLED BACK",
            "normalized_description": "should be rolled back",
            "transaction_type": "DEBIT",
            "amount_paise": 99900,
            "category": "Uncategorized",
            "rule_id": "R_UNKNOWN_DEBIT",
        }
    ]

    with pytest.raises(sqlite3.DatabaseError, match="Simulated database abort"):
        replace_transactions(db_path, new_batch)

    # Remove the trigger to allow reading/inspecting cleanly
    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute("DROP TRIGGER abort_insert_trigger;")
    finally:
        conn.close()

    # The rollback MUST have preserved the original 3 records!
    current_rows = read_transactions(db_path)
    assert len(current_rows) == 3
    assert current_rows == initial_rows


def test_cursor_failure_rolls_back_and_preserves_old_records(
    db_path, sample_valid_records, monkeypatch
):
    """
    Simulate a cursor-level OperationalError (e.g. disk I/O failure) during executemany.
    Confirms that Python's 'with conn:' context manager issues a rollback on exception.
    """
    replace_transactions(db_path, sample_valid_records)
    initial_rows = read_transactions(db_path)
    assert len(initial_rows) == 3

    new_batch = [
        {
            "transaction_date": "2026-10-20",
            "description": "SHOULD BE ROLLED BACK",
            "normalized_description": "should be rolled back",
            "transaction_type": "DEBIT",
            "amount_paise": 99900,
            "category": "Uncategorized",
            "rule_id": "R_UNKNOWN_DEBIT",
        }
    ]

    orig_get_connection = storage_module_get_connection = get_connection

    class FailingCursor:
        def __init__(self, real_cur):
            self._real = real_cur

        def execute(self, *args, **kwargs):
            return self._real.execute(*args, **kwargs)

        def executemany(self, *args, **kwargs):
            raise sqlite3.OperationalError("Simulated disk I/O error during executemany")

        def __getattr__(self, name):
            return getattr(self._real, name)

    class FailingConnection:
        def __init__(self, real_conn):
            self._real = real_conn

        def cursor(self):
            return FailingCursor(self._real.cursor())

        def __enter__(self):
            return self._real.__enter__()

        def __exit__(self, exc_type, exc_val, exc_tb):
            return self._real.__exit__(exc_type, exc_val, exc_tb)

        def close(self):
            return self._real.close()

        def __getattr__(self, name):
            return getattr(self._real, name)

    def patched_get_connection(path):
        real_conn = orig_get_connection(path)
        return FailingConnection(real_conn)

    monkeypatch.setattr("storage.get_connection", patched_get_connection)

    with pytest.raises(sqlite3.OperationalError, match="Simulated disk I/O error"):
        replace_transactions(db_path, new_batch)

    monkeypatch.undo()

    # The rollback MUST have preserved the original 3 records!
    current_rows = read_transactions(db_path)
    assert len(current_rows) == 3
    assert current_rows == initial_rows


def test_connection_closed_on_success_and_error(db_path, sample_valid_records, monkeypatch):
    """Verify that replace_transactions closes the database connection on success and error."""
    close_calls = []
    orig_get_connection = get_connection

    class TrackingConnection:
        def __init__(self, real_conn):
            self._real = real_conn

        def close(self):
            close_calls.append(True)
            return self._real.close()

        def __enter__(self):
            return self._real.__enter__()

        def __exit__(self, *args):
            return self._real.__exit__(*args)

        def __getattr__(self, name):
            return getattr(self._real, name)

    def tracking_get_conn(path):
        return TrackingConnection(orig_get_connection(path))

    monkeypatch.setattr("storage.get_connection", tracking_get_conn)

    # 1. Success case
    replace_transactions(db_path, sample_valid_records)
    # At least two get_connection calls: initialize_database and replace_transactions
    assert len(close_calls) >= 2
    assert all(close_calls)

    # 2. Failure case during execution
    close_calls.clear()

    class FailingCursor:
        def execute(self, *a, **k):
            raise sqlite3.OperationalError("Forced failure")

    class FailingTrackingConn(TrackingConnection):
        def cursor(self):
            return FailingCursor()

    monkeypatch.setattr("storage.get_connection", lambda p: FailingTrackingConn(orig_get_connection(p)))

    with pytest.raises(sqlite3.OperationalError, match="Forced failure"):
        replace_transactions(db_path, sample_valid_records)

    assert len(close_calls) >= 1
    assert all(close_calls)


# ============================================================================
# Section 8: Parameterized SQL & Injection Safety
# ============================================================================

def test_sql_injection_safety_with_special_characters(db_path):
    """
    Test that malicious SQL payloads and unusual characters in descriptions
    are safely parameterized with '?' placeholders and never executed as raw SQL.
    """
    malicious_record = [
        {
            "transaction_date": "2026-10-01",
            "description": "Robert'); DROP TABLE transactions;--",
            "normalized_description": "robert'); drop table transactions;--",
            "transaction_type": "DEBIT",
            "amount_paise": 1000,
            "category": "Uncategorized",
            "rule_id": "R_UNKNOWN_DEBIT",
        }
    ]

    # Must succeed without dropping the table
    replace_transactions(db_path, malicious_record)

    rows = read_transactions(db_path)
    assert len(rows) == 1
    # Verify description was preserved literally
    assert rows[0]["description"] == "Robert'); DROP TABLE transactions;--"

    # Confirm table still exists
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transactions';")
        assert cur.fetchone() is not None
    finally:
        conn.close()


# ============================================================================
# Section 9: validate_record_for_storage Unit Tests
# ============================================================================

def test_validate_record_for_storage_boolean_amount_rejected():
    """Booleans (True/False) are subclasses of int in Python but must be rejected."""
    bad_record = {
        "transaction_date": "2026-10-01",
        "description": "Test",
        "normalized_description": "test",
        "transaction_type": "DEBIT",
        "amount_paise": True,  # True == 1 in Python int comparison
        "category": "Uncategorized",
        "rule_id": "R_UNKNOWN_DEBIT",
    }
    with pytest.raises(ValueError, match="amount_paise"):
        validate_record_for_storage(bad_record)


def test_validate_record_for_storage_integer_bounds():
    """
    Phase 8 Regression Test (Defect 2):
    Verify that validate_record_for_storage accepts the maximum 64-bit integer
    (9223372036854775807) and rejects any integer exceeding that limit.
    """
    base_record = {
        "transaction_date": "2026-10-01",
        "description": "Test Bounds",
        "normalized_description": "test bounds",
        "transaction_type": "DEBIT",
        "category": "Uncategorized",
        "rule_id": "R_UNKNOWN_DEBIT",
    }

    # Maximum 64-bit integer passes
    valid_record = {**base_record, "amount_paise": MAX_SQLITE_INTEGER}
    validate_record_for_storage(valid_record)

    # Maximum + 1 is rejected cleanly
    overflow_record = {**base_record, "amount_paise": MAX_SQLITE_INTEGER + 1}
    with pytest.raises(ValueError, match="exceeds maximum supported SQLite integer limit"):
        validate_record_for_storage(overflow_record)

    # Astronomical amount (10^21 paise) is rejected cleanly
    astronomical_record = {**base_record, "amount_paise": 10**21}
    with pytest.raises(ValueError, match="exceeds maximum supported SQLite integer limit"):
        validate_record_for_storage(astronomical_record)


def test_replace_transactions_with_max_integer_persists_cleanly(db_path):
    """Verify that a record with MAX_SQLITE_INTEGER is persisted and read back cleanly."""
    max_record = [
        {
            "transaction_date": "2026-10-01",
            "description": "Max Int Test",
            "normalized_description": "max int test",
            "transaction_type": "DEBIT",
            "amount_paise": MAX_SQLITE_INTEGER,
            "category": "Uncategorized",
            "rule_id": "R_UNKNOWN_DEBIT",
        }
    ]
    count = replace_transactions(db_path, max_record)
    assert count == 1

    rows = read_transactions(db_path)
    assert len(rows) == 1
    assert rows[0]["amount_paise"] == MAX_SQLITE_INTEGER


def test_replace_transactions_overflow_preserves_database(db_path, sample_valid_records):
    """Verify that an oversized integer rejection preserves an existing database intact."""
    # Seed database with initial valid records
    replace_transactions(db_path, sample_valid_records)
    initial_rows = read_transactions(db_path)
    assert len(initial_rows) == 3

    # Attempt replacement with an oversized integer record
    overflow_batch = [
        {
            "transaction_date": "2026-10-01",
            "description": "Overflow Attempt",
            "normalized_description": "overflow attempt",
            "transaction_type": "DEBIT",
            "amount_paise": MAX_SQLITE_INTEGER + 1,
            "category": "Uncategorized",
            "rule_id": "R_UNKNOWN_DEBIT",
        }
    ]

    with pytest.raises(ValueError, match="exceeds maximum supported SQLite integer limit"):
        replace_transactions(db_path, overflow_batch)

    # Prior dataset remains intact
    preserved_rows = read_transactions(db_path)
    assert len(preserved_rows) == 3
    assert [r["description"] for r in preserved_rows] == [r["description"] for r in initial_rows]
