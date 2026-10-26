"""
SpendSense — SQLite Storage & Atomic Dataset Replacement Module.

This module implements Milestone 3:
1. SQLite schema definition: single 'transactions' table with strict column constraints.
2. Parameterized SQL operations using standard-library sqlite3 ('?' placeholders, no string interpolation).
3. Atomic replacement policy:
   - Input validation precedes any database modification.
   - Empty or invalid input records preserve the existing database.
   - Old rows are deleted and new rows inserted within a single transaction.
   - Rolls back completely if any insertion fails.
   - Replaces the previous dataset on a successful import (no append duplication).
   - Preserves duplicate-looking records inside a single input batch.
"""

from pathlib import Path
import sqlite3
from typing import Any

# Table name and schema definition
TABLE_NAME = "transactions"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY,
    transaction_date TEXT NOT NULL,
    description TEXT NOT NULL,
    normalized_description TEXT NOT NULL,
    transaction_type TEXT NOT NULL
        CHECK (transaction_type IN ('DEBIT', 'CREDIT')),
    amount_paise INTEGER NOT NULL CHECK (amount_paise > 0),
    category TEXT NOT NULL,
    rule_id TEXT NOT NULL
);
"""

# Required keys for a fully prepared transaction record
REQUIRED_RECORD_KEYS = (
    "transaction_date",
    "description",
    "normalized_description",
    "transaction_type",
    "amount_paise",
    "category",
    "rule_id",
)


# Maximum signed 64-bit integer supported by SQLite INTEGER (2^63 - 1)
MAX_SQLITE_INTEGER: int = 9223372036854775807


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    """Return a new sqlite3 Connection with row_factory set to sqlite3.Row."""
    path = str(db_path)
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database(db_path: str | Path) -> None:
    """Create the transactions table and constraints if they do not already exist."""
    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute(SCHEMA_SQL)
    finally:
        conn.close()


def validate_record_for_storage(record: dict[str, Any]) -> None:
    """
    Validate that a record dictionary satisfies the storage schema contract.
    Raises ValueError if any field is missing or invalid.
    """
    if not isinstance(record, dict):
        raise ValueError(f"Record must be a dictionary, got: {type(record).__name__}")

    for key in REQUIRED_RECORD_KEYS:
        if key not in record:
            raise ValueError(f"Record missing required key: '{key}'")

    if not isinstance(record["transaction_date"], str) or not record["transaction_date"].strip():
        raise ValueError("transaction_date must be a non-empty string")

    if not isinstance(record["description"], str) or not record["description"].strip():
        raise ValueError("description must be a non-empty string")

    if not isinstance(record["normalized_description"], str):
        raise ValueError("normalized_description must be a string")

    if record["transaction_type"] not in ("DEBIT", "CREDIT"):
        raise ValueError(
            f"transaction_type must be 'DEBIT' or 'CREDIT', got: '{record['transaction_type']}'"
        )

    amount = record["amount_paise"]
    # In Python, bool is a subclass of int, so exclude bool explicitly
    if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
        raise ValueError(f"amount_paise must be a positive integer, got: {amount!r}")

    if amount > MAX_SQLITE_INTEGER:
        raise ValueError(
            f"amount_paise exceeds maximum supported SQLite integer limit ({MAX_SQLITE_INTEGER}), got: {amount}"
        )

    if not isinstance(record["category"], str) or not record["category"].strip():
        raise ValueError("category must be a non-empty string")

    if not isinstance(record["rule_id"], str) or not record["rule_id"].strip():
        raise ValueError("rule_id must be a non-empty string")


def replace_transactions(db_path: str | Path, records: list[dict[str, Any]]) -> int:
    """
    Atomically replace all rows in the transactions table with the provided records.

    Requirements:
    1. Validate all records before modifying the database.
    2. Empty or zero-length records raise ValueError; existing database contents are preserved.
    3. Ensure table exists.
    4. Delete existing rows and insert new rows within a single transaction.
    5. Roll back on any failure so previous rows remain intact.
    6. Return the count of inserted records.

    Raises:
    - ValueError if records is empty, not a list, or contains invalid record data.
    - sqlite3.Error if a database failure occurs (transaction is rolled back).
    """
    if records is None or not isinstance(records, list):
        raise ValueError("records must be a non-empty list of transaction dictionaries")

    if len(records) == 0:
        raise ValueError("Cannot replace transactions: record list is empty (prior dataset preserved)")

    # 1. Validate all records in memory BEFORE touching the database
    for idx, record in enumerate(records):
        try:
            validate_record_for_storage(record)
        except ValueError as e:
            raise ValueError(f"Record at index {idx} failed storage validation: {e}") from e

    # Prepare parameterized tuples for executemany
    params = [
        (
            r["transaction_date"],
            r["description"],
            r["normalized_description"],
            r["transaction_type"],
            r["amount_paise"],
            r["category"],
            r["rule_id"],
        )
        for r in records
    ]

    # Ensure table exists
    initialize_database(db_path)

    # 2. Atomic replacement inside a single database transaction
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM transactions;")
            cursor.executemany(
                """
                INSERT INTO transactions (
                    transaction_date,
                    description,
                    normalized_description,
                    transaction_type,
                    amount_paise,
                    category,
                    rule_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                params,
            )
        return len(records)
    except OverflowError as e:
        raise ValueError(
            f"Database insertion failed: integer value exceeds SQLite limit: {e}"
        ) from e
    finally:
        conn.close()


def read_transactions(db_path: str | Path) -> list[dict[str, Any]]:
    """
    Read and return all transaction rows currently stored in SQLite.

    Returns a list of dictionaries with keys:
    id, transaction_date, description, normalized_description, transaction_type,
    amount_paise, category, rule_id.
    """
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        # Verify if table exists before querying
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='transactions';"
        )
        if not cur.fetchone():
            return []

        cur.execute(
            """
            SELECT
                id,
                transaction_date,
                description,
                normalized_description,
                transaction_type,
                amount_paise,
                category,
                rule_id
            FROM transactions
            ORDER BY id ASC;
            """
        )
        rows = [dict(row) for row in cur.fetchall()]
        return rows
    finally:
        conn.close()
