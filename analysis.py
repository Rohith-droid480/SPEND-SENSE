"""
SpendSense — Analysis & Potential-Outlier Screening Module.

This module implements Milestone 4:
1. SQL Aggregation Summaries:
   - Overall expense totals (DEBIT only, excluding Transfer).
   - Expense totals and transaction counts grouped by category.
   - Credit totals and transaction counts grouped by category (Income, Refund, Other Credit, etc.).
   - Separate transfers summary (including DEBIT and CREDIT transfers).
   - Deterministic handling of empty databases without SQL NULL failures.
   - All monetary amounts maintained strictly in integer paise.

2. Potential-Outlier Screening:
   - Category-specific Modified Z-scores based on raw Median Absolute Deviation (MAD).
   - Eligible records: DEBIT transactions excluding Transfer.
   - Completely independent category baselines.
   - Minimum sample size guardrail: at least 5 eligible observations in the category.
   - Explicit handling of insufficient history (NOT_EVALUATED_INSUFFICIENT_DATA).
   - Explicit handling of zero MAD (NOT_EVALUATED_ZERO_MAD) with zero-division protection.
   - Exact scaling factor: 0.6745 applied exactly once.
   - Strict threshold: abs(ModifiedZ) > 3.5.
   - Cautious wording: 'potential outlier' or 'potentially unusual expense', never 'fraud'.
"""

from pathlib import Path
import sqlite3
import statistics
from typing import Any

from storage import get_connection

# Mathematical and evaluation constants
OUTLIER_THRESHOLD = 3.5
MIN_OBSERVATIONS = 5
SCALE_FACTOR = 0.6745

# Explicit status codes for categories that cannot be evaluated
STATUS_INSUFFICIENT_DATA = "NOT_EVALUATED_INSUFFICIENT_DATA"
STATUS_ZERO_MAD = "NOT_EVALUATED_ZERO_MAD"


def _table_exists(conn: sqlite3.Connection, table_name: str = "transactions") -> bool:
    """Check whether the transactions table exists in the database."""
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?;",
        (table_name,),
    )
    return cur.fetchone() is not None


def calculate_summary(db_path: str | Path) -> dict[str, Any]:
    """
    Calculate spending, credit, and transfer summaries using SQLite aggregation.

    Requirements:
    1. Overall expenses: DEBIT only, category <> 'Transfer'. Total in integer paise.
    2. Expense totals by category: grouped by category, ordered by total_paise DESC, category ASC.
    3. Credits: CREDIT transactions reported separately, grouped by category.
    4. Transfers: reported in a dedicated summary section, separate from expenses.
    5. Empty database: returns deterministic zero totals and empty lists (handles SQL NULL safely).
    6. All monetary values are integer paise; no float conversion.

    Returns a dictionary with keys:
    - total_expenses_paise: int
    - expenses_by_category: list[dict] with keys: category, total_paise, transaction_count
    - total_credits_paise: int
    - credits_by_category: list[dict] with keys: category, total_paise, transaction_count
    - transfers: dict with keys: total_paise, transaction_count, by_type (list[dict])
    """
    empty_summary: dict[str, Any] = {
        "total_expenses_paise": 0,
        "expenses_by_category": [],
        "total_credits_paise": 0,
        "credits_by_category": [],
        "transfers": {
            "total_paise": 0,
            "transaction_count": 0,
            "by_type": [],
        },
    }

    conn = get_connection(db_path)
    try:
        if not _table_exists(conn):
            return empty_summary

        cur = conn.cursor()

        # 1. Overall expenses: DEBIT only, excluding Transfer
        cur.execute(
            """
            SELECT COALESCE(SUM(amount_paise), 0) AS total_paise
            FROM transactions
            WHERE transaction_type = 'DEBIT' AND category <> 'Transfer';
            """
        )
        row = cur.fetchone()
        total_expenses_paise = int(row["total_paise"]) if row else 0

        # 2. Expenses by category: DEBIT only, excluding Transfer
        cur.execute(
            """
            SELECT
                category,
                SUM(amount_paise) AS total_paise,
                COUNT(*) AS transaction_count
            FROM transactions
            WHERE transaction_type = 'DEBIT' AND category <> 'Transfer'
            GROUP BY category
            ORDER BY total_paise DESC, category ASC;
            """
        )
        expenses_by_category = [
            {
                "category": str(r["category"]),
                "total_paise": int(r["total_paise"]),
                "transaction_count": int(r["transaction_count"]),
            }
            for r in cur.fetchall()
        ]

        # 3. Total credits
        cur.execute(
            """
            SELECT COALESCE(SUM(amount_paise), 0) AS total_paise
            FROM transactions
            WHERE transaction_type = 'CREDIT';
            """
        )
        row = cur.fetchone()
        total_credits_paise = int(row["total_paise"]) if row else 0

        # 4. Credits by category (Income, Refund, Other Credit, Transfer, etc.)
        cur.execute(
            """
            SELECT
                category,
                SUM(amount_paise) AS total_paise,
                COUNT(*) AS transaction_count
            FROM transactions
            WHERE transaction_type = 'CREDIT'
            GROUP BY category
            ORDER BY total_paise DESC, category ASC;
            """
        )
        credits_by_category = [
            {
                "category": str(r["category"]),
                "total_paise": int(r["total_paise"]),
                "transaction_count": int(r["transaction_count"]),
            }
            for r in cur.fetchall()
        ]

        # 5. Transfers summary: all transactions categorized as 'Transfer'
        cur.execute(
            """
            SELECT
                COALESCE(SUM(amount_paise), 0) AS total_paise,
                COUNT(*) AS transaction_count
            FROM transactions
            WHERE category = 'Transfer';
            """
        )
        row = cur.fetchone()
        transfers_total_paise = int(row["total_paise"]) if row else 0
        transfers_count = int(row["transaction_count"]) if row else 0

        cur.execute(
            """
            SELECT
                transaction_type,
                SUM(amount_paise) AS total_paise,
                COUNT(*) AS transaction_count
            FROM transactions
            WHERE category = 'Transfer'
            GROUP BY transaction_type
            ORDER BY transaction_type ASC;
            """
        )
        transfers_by_type = [
            {
                "transaction_type": str(r["transaction_type"]),
                "total_paise": int(r["total_paise"]),
                "transaction_count": int(r["transaction_count"]),
            }
            for r in cur.fetchall()
        ]

        return {
            "total_expenses_paise": total_expenses_paise,
            "expenses_by_category": expenses_by_category,
            "total_credits_paise": total_credits_paise,
            "credits_by_category": credits_by_category,
            "transfers": {
                "total_paise": transfers_total_paise,
                "transaction_count": transfers_count,
                "by_type": transfers_by_type,
            },
        }
    finally:
        conn.close()


def compute_modified_z_score(value: int | float, median_x: float, mad: float) -> float:
    """
    Calculate the Modified Z-score using raw MAD:
    ModifiedZ = 0.6745 * (value - median_x) / MAD

    The scaling factor 0.6745 is applied exactly once.
    Raises ValueError if mad == 0 to prevent division by zero.
    """
    if mad == 0:
        raise ValueError("Cannot calculate Modified Z-score when raw MAD is 0 (division by zero)")
    return SCALE_FACTOR * (value - median_x) / mad


def is_potential_outlier(score: float) -> bool:
    """
    Check if a score strictly exceeds the outlier threshold:
    abs(score) > 3.5.

    A score exactly equal to 3.5 does NOT qualify.
    """
    return abs(score) > OUTLIER_THRESHOLD


def detect_potential_outliers(db_path: str | Path) -> dict[str, Any]:
    """
    Screen eligible debit expenses for potential outliers using category-specific Modified Z-scores.

    Algorithm & Guardrails:
    1. Eligible transactions: DEBIT only, category <> 'Transfer'.
    2. Independent category baselines: amounts from different categories are never pooled.
    3. Minimum sample size: at least 5 eligible transactions in the category (including candidate).
       If fewer than 5: status is NOT_EVALUATED_INSUFFICIENT_DATA.
    4. Zero raw MAD: if MAD == 0: status is NOT_EVALUATED_ZERO_MAD.
    5. Scoring: ModifiedZ = 0.6745 * (amount_paise - median) / raw_MAD.
    6. Threshold: strictly abs(ModifiedZ) > 3.5.
    7. Flagged transactions are described as 'potential outliers', never 'fraud'.

    Returns a dictionary with keys:
    - potential_outliers: list[dict] of flagged transactions with fields:
        id, transaction_date, description, category, amount_paise, modified_z_score, explanation
    - not_evaluated: list[dict] of categories that could not be evaluated with fields:
        category, status, reason, transaction_count
    """
    empty_result: dict[str, Any] = {
        "potential_outliers": [],
        "not_evaluated": [],
    }

    conn = get_connection(db_path)
    try:
        if not _table_exists(conn):
            return empty_result

        cur = conn.cursor()

        # Query eligible debit expenses, strictly excluding transfers
        cur.execute(
            """
            SELECT
                id,
                transaction_date,
                description,
                category,
                amount_paise
            FROM transactions
            WHERE transaction_type = 'DEBIT' AND category <> 'Transfer'
            ORDER BY category ASC, id ASC;
            """
        )
        rows = cur.fetchall()
        if not rows:
            return empty_result

        # Group rows by category
        records_by_category: dict[str, list[sqlite3.Row]] = {}
        for row in rows:
            cat = str(row["category"])
            if cat not in records_by_category:
                records_by_category[cat] = []
            records_by_category[cat].append(row)

        potential_outliers: list[dict[str, Any]] = []
        not_evaluated: list[dict[str, Any]] = []

        # Evaluate each category independently
        for category, cat_rows in records_by_category.items():
            amounts = [int(r["amount_paise"]) for r in cat_rows]
            n = len(amounts)

            # Guardrail 1: Minimum sample size of 5
            if n < MIN_OBSERVATIONS:
                not_evaluated.append(
                    {
                        "category": category,
                        "status": STATUS_INSUFFICIENT_DATA,
                        "reason": (
                            f"Category '{category}' has only {n} eligible transaction(s); "
                            f"at least {MIN_OBSERVATIONS} are required for screening."
                        ),
                        "transaction_count": n,
                    }
                )
                continue

            # Compute median of category amounts
            median_x = float(statistics.median(amounts))

            # Compute raw MAD: median of absolute deviations from median_x
            abs_deviations = [abs(val - median_x) for val in amounts]
            mad = float(statistics.median(abs_deviations))

            # Guardrail 2: Raw MAD equals zero (cannot divide by zero)
            if mad == 0.0:
                not_evaluated.append(
                    {
                        "category": category,
                        "status": STATUS_ZERO_MAD,
                        "reason": (
                            f"Category '{category}' has a raw MAD of 0 (identical amounts); "
                            "dispersion cannot be evaluated."
                        ),
                        "transaction_count": n,
                    }
                )
                continue

            # Evaluate each candidate transaction against its category baseline
            for r in cat_rows:
                val = int(r["amount_paise"])
                score = compute_modified_z_score(val, median_x, mad)

                if is_potential_outlier(score):
                    potential_outliers.append(
                        {
                            "id": int(r["id"]),
                            "transaction_date": str(r["transaction_date"]),
                            "description": str(r["description"]),
                            "category": category,
                            "amount_paise": val,
                            "modified_z_score": score,
                            "explanation": (
                                f"Potential outlier: Modified Z-score of {score:.2f} "
                                f"strictly exceeds threshold {OUTLIER_THRESHOLD}."
                            ),
                        }
                    )

        # Deterministic ordering
        # Sort outliers by highest absolute score first, with id as tie-breaker
        potential_outliers.sort(key=lambda item: (-abs(item["modified_z_score"]), item["id"]))
        # Sort not-evaluated categories alphabetically
        not_evaluated.sort(key=lambda item: item["category"])

        return {
            "potential_outliers": potential_outliers,
            "not_evaluated": not_evaluated,
        }
    finally:
        conn.close()
