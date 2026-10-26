"""
SpendSense — Milestone 4 Tests: SQL Summaries & Potential-Outlier Screening.

Covers:
1. SQL Summaries (calculate_summary):
   - Hand-computed overall expense total (DEBIT only, excluding Transfer).
   - Hand-computed expense totals and counts by category.
   - Exclusion of DEBIT transfers from expense totals.
   - Exclusion of CREDIT transfers from expense totals.
   - Separate reporting of credits grouped by inferred category.
   - Preservation of refund credits (never netted against expenses).
   - Dedicated transfers summary section (DEBIT and CREDIT transfers).
   - Deterministic handling of empty databases and non-existent databases (no SQL NULL failures).
   - Identical-looking legitimate transactions counted independently.
   - Deterministic output ordering (descending total with category tie-breaker).

2. Potential-Outlier Screening (detect_potential_outliers):
   - Category with < 5 eligible observations returns NOT_EVALUATED_INSUFFICIENT_DATA.
   - Category with exactly 5 eligible observations evaluated when raw MAD > 0.
   - Clear extreme synthetic expense flagged as potential outlier.
   - Normal eligible expense not flagged in the same dataset.
   - Category with zero raw MAD returns NOT_EVALUATED_ZERO_MAD.
   - Protection against division by zero.
   - CREDIT transactions never screened as expense outliers.
   - Transfer transactions excluded from both baseline and candidate screening.
   - Completely independent category baselines (no cross-category leakage).
   - Scores associated with the correct stored transaction record.
   - Scaling factor 0.6745 applied exactly once.
   - Strict threshold abs(score) > 3.5: exact 3.5 is not flagged, 3.5001 is flagged.
   - Unit tests for compute_modified_z_score and is_potential_outlier.
   - Non-fraud wording verified in outputs.
"""

from pathlib import Path
import pytest

from analysis import (
    MIN_OBSERVATIONS,
    OUTLIER_THRESHOLD,
    SCALE_FACTOR,
    STATUS_INSUFFICIENT_DATA,
    STATUS_ZERO_MAD,
    calculate_summary,
    compute_modified_z_score,
    detect_potential_outliers,
    is_potential_outlier,
)
from storage import initialize_database, replace_transactions


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Fixture providing a temporary database file path."""
    return tmp_path / "test_spendsense_m4.db"


@pytest.fixture
def summary_sample_records() -> list[dict]:
    """
    Standard dataset with hand-verifiable totals:
    - 3 Groceries DEBIT: 2000, 3000, 3000 paise -> Total: 8000 paise, count: 3
    - 1 Dining DEBIT: 5000 paise -> Total: 5000 paise, count: 1
    - 1 Subscriptions DEBIT: 1500 paise -> Total: 1500 paise, count: 1
    - 1 Transfer DEBIT: 10000 paise -> Excluded from expenses!
    - 1 Income CREDIT: 500000 paise -> Total: 500000 paise, count: 1
    - 1 Refund CREDIT: 1200 paise -> Total: 1200 paise, count: 1 (not netted)
    - 1 Transfer CREDIT: 25000 paise -> Total: 25000 paise, count: 1
    - 1 Other Credit CREDIT: 500 paise -> Total: 500 paise, count: 1

    Expected Totals:
    - Overall Expenses = 8000 + 5000 + 1500 = 14500 paise (Transfers excluded)
    - Total Credits = 500000 + 1200 + 25000 + 500 = 526700 paise
    - Total Transfers = 10000 (DEBIT) + 25000 (CREDIT) = 35000 paise, count: 2
    """
    return [
        {
            "transaction_date": "2026-10-01",
            "description": "GROCERY STORE A",
            "normalized_description": "grocery store a",
            "transaction_type": "DEBIT",
            "amount_paise": 2000,
            "category": "Groceries",
            "rule_id": "R_GROCERIES",
        },
        {
            "transaction_date": "2026-10-02",
            "description": "GROCERY STORE B",
            "normalized_description": "grocery store b",
            "transaction_type": "DEBIT",
            "amount_paise": 3000,
            "category": "Groceries",
            "rule_id": "R_GROCERIES",
        },
        {
            "transaction_date": "2026-10-03",
            "description": "GROCERY STORE B DUP",
            "normalized_description": "grocery store b dup",
            "transaction_type": "DEBIT",
            "amount_paise": 3000,
            "category": "Groceries",
            "rule_id": "R_GROCERIES",
        },
        {
            "transaction_date": "2026-10-04",
            "description": "RESTAURANT CAFE",
            "normalized_description": "restaurant cafe",
            "transaction_type": "DEBIT",
            "amount_paise": 5000,
            "category": "Dining",
            "rule_id": "R_DINING",
        },
        {
            "transaction_date": "2026-10-05",
            "description": "NETFLIX MONTHLY",
            "normalized_description": "netflix monthly",
            "transaction_type": "DEBIT",
            "amount_paise": 1500,
            "category": "Subscriptions",
            "rule_id": "R_SUBSCRIPTION",
        },
        {
            "transaction_date": "2026-10-06",
            "description": "TRANSFER TO SAVINGS",
            "normalized_description": "transfer to savings",
            "transaction_type": "DEBIT",
            "amount_paise": 10000,
            "category": "Transfer",
            "rule_id": "R_TRANSFER",
        },
        {
            "transaction_date": "2026-10-07",
            "description": "MONTHLY SALARY",
            "normalized_description": "monthly salary",
            "transaction_type": "CREDIT",
            "amount_paise": 500000,
            "category": "Income",
            "rule_id": "R_INCOME",
        },
        {
            "transaction_date": "2026-10-08",
            "description": "MERCHANT REFUND",
            "normalized_description": "merchant refund",
            "transaction_type": "CREDIT",
            "amount_paise": 1200,
            "category": "Refund",
            "rule_id": "R_REFUND",
        },
        {
            "transaction_date": "2026-10-09",
            "description": "INCOMING TRANSFER",
            "normalized_description": "incoming transfer",
            "transaction_type": "CREDIT",
            "amount_paise": 25000,
            "category": "Transfer",
            "rule_id": "R_TRANSFER",
        },
        {
            "transaction_date": "2026-10-10",
            "description": "CASHBACK REWARD",
            "normalized_description": "cashback reward",
            "transaction_type": "CREDIT",
            "amount_paise": 500,
            "category": "Other Credit",
            "rule_id": "R_UNKNOWN_CREDIT",
        },
    ]


# ============================================================================
# Section 1: SQL Summary Tests (calculate_summary)
# ============================================================================

def test_calculate_summary_hand_computed_totals(db_path, summary_sample_records):
    """Test calculate_summary produces exact hand-computed totals for all components."""
    replace_transactions(db_path, summary_sample_records)

    summary = calculate_summary(db_path)

    # 1. Overall expenses: exactly 14,500 paise (Groceries 8000 + Dining 5000 + Subscriptions 1500)
    assert summary["total_expenses_paise"] == 14500
    assert isinstance(summary["total_expenses_paise"], int)

    # 2. Expenses by category
    exp_cats = {item["category"]: item for item in summary["expenses_by_category"]}
    assert len(exp_cats) == 3

    assert exp_cats["Groceries"]["total_paise"] == 8000
    assert exp_cats["Groceries"]["transaction_count"] == 3

    assert exp_cats["Dining"]["total_paise"] == 5000
    assert exp_cats["Dining"]["transaction_count"] == 1

    assert exp_cats["Subscriptions"]["total_paise"] == 1500
    assert exp_cats["Subscriptions"]["transaction_count"] == 1

    # Transfer must NOT be in expenses_by_category
    assert "Transfer" not in exp_cats

    # 3. Total credits: exactly 526,700 paise (500000 + 1200 + 25000 + 500)
    assert summary["total_credits_paise"] == 526700
    assert isinstance(summary["total_credits_paise"], int)

    # 4. Credits by category
    credit_cats = {item["category"]: item for item in summary["credits_by_category"]}
    assert len(credit_cats) == 4

    assert credit_cats["Income"]["total_paise"] == 500000
    assert credit_cats["Income"]["transaction_count"] == 1

    assert credit_cats["Transfer"]["total_paise"] == 25000
    assert credit_cats["Transfer"]["transaction_count"] == 1

    assert credit_cats["Refund"]["total_paise"] == 1200
    assert credit_cats["Refund"]["transaction_count"] == 1

    assert credit_cats["Other Credit"]["total_paise"] == 500
    assert credit_cats["Other Credit"]["transaction_count"] == 1

    # 5. Transfers summary: exactly 35,000 paise (DEBIT 10000 + CREDIT 25000)
    transfers = summary["transfers"]
    assert transfers["total_paise"] == 35000
    assert transfers["transaction_count"] == 2

    by_type = {item["transaction_type"]: item for item in transfers["by_type"]}
    assert by_type["DEBIT"]["total_paise"] == 10000
    assert by_type["DEBIT"]["transaction_count"] == 1

    assert by_type["CREDIT"]["total_paise"] == 25000
    assert by_type["CREDIT"]["transaction_count"] == 1


def test_calculate_summary_deterministic_ordering(db_path, summary_sample_records):
    """Test expenses and credits are ordered deterministically by total_paise DESC, category ASC."""
    replace_transactions(db_path, summary_sample_records)

    summary = calculate_summary(db_path)

    # Expenses: 8000 (Groceries) > 5000 (Dining) > 1500 (Subscriptions)
    exp_order = [item["category"] for item in summary["expenses_by_category"]]
    assert exp_order == ["Groceries", "Dining", "Subscriptions"]

    # Credits: 500000 (Income) > 25000 (Transfer) > 1200 (Refund) > 500 (Other Credit)
    credit_order = [item["category"] for item in summary["credits_by_category"]]
    assert credit_order == ["Income", "Transfer", "Refund", "Other Credit"]


def test_calculate_summary_empty_database(db_path):
    """Test calculate_summary returns clean zero totals and empty lists on an empty table."""
    initialize_database(db_path)

    summary = calculate_summary(db_path)

    assert summary["total_expenses_paise"] == 0
    assert summary["expenses_by_category"] == []
    assert summary["total_credits_paise"] == 0
    assert summary["credits_by_category"] == []
    assert summary["transfers"]["total_paise"] == 0
    assert summary["transfers"]["transaction_count"] == 0
    assert summary["transfers"]["by_type"] == []


def test_calculate_summary_nonexistent_database(tmp_path):
    """Test calculate_summary returns deterministic empty summary if database file has no table."""
    nonexistent = tmp_path / "no_such_file.db"
    summary = calculate_summary(nonexistent)

    assert summary["total_expenses_paise"] == 0
    assert summary["expenses_by_category"] == []
    assert summary["total_credits_paise"] == 0
    assert summary["credits_by_category"] == []
    assert summary["transfers"]["total_paise"] == 0
    assert summary["transfers"]["transaction_count"] == 0
    assert summary["transfers"]["by_type"] == []


def test_calculate_summary_refunds_not_netted_against_purchases(db_path):
    """
    CRITICAL REQUIREMENT:
    Refunds must be reported as credits and NEVER subtracted from purchase totals.
    """
    records = [
        {
            "transaction_date": "2026-10-01",
            "description": "AMAZON PURCHASE",
            "normalized_description": "amazon purchase",
            "transaction_type": "DEBIT",
            "amount_paise": 10000,
            "category": "Groceries",
            "rule_id": "R_GROCERIES",
        },
        {
            "transaction_date": "2026-10-02",
            "description": "AMAZON REFUND",
            "normalized_description": "amazon refund",
            "transaction_type": "CREDIT",
            "amount_paise": 10000,
            "category": "Refund",
            "rule_id": "R_REFUND",
        },
    ]
    replace_transactions(db_path, records)

    summary = calculate_summary(db_path)

    # Expenses must remain exactly 10,000 paise (NOT 0 paise!)
    assert summary["total_expenses_paise"] == 10000
    assert summary["expenses_by_category"][0]["total_paise"] == 10000

    # Refund is reported in credits
    assert summary["total_credits_paise"] == 10000
    assert summary["credits_by_category"][0]["category"] == "Refund"
    assert summary["credits_by_category"][0]["total_paise"] == 10000


def test_calculate_summary_debit_transfer_excluded_from_expenses(db_path):
    """Test that a DEBIT categorized as Transfer does not count toward expense totals."""
    records = [
        {
            "transaction_date": "2026-10-01",
            "description": "TRANSFER FUNDS",
            "normalized_description": "transfer funds",
            "transaction_type": "DEBIT",
            "amount_paise": 999999,
            "category": "Transfer",
            "rule_id": "R_TRANSFER",
        }
    ]
    replace_transactions(db_path, records)

    summary = calculate_summary(db_path)

    # Expenses must be 0
    assert summary["total_expenses_paise"] == 0
    assert summary["expenses_by_category"] == []

    # Transfers must show the 999,999 paise debit
    assert summary["transfers"]["total_paise"] == 999999
    assert summary["transfers"]["transaction_count"] == 1
    assert summary["transfers"]["by_type"][0]["transaction_type"] == "DEBIT"


# ============================================================================
# Section 2: Mathematical Helper Unit Tests
# ============================================================================

def test_compute_modified_z_score_scaling_factor_applied_once():
    """Verify compute_modified_z_score applies exactly 0.6745 once with raw MAD."""
    # (value - median) = 1000, mad = 1000 -> ModifiedZ = 0.6745 * 1000 / 1000 = 0.6745
    score = compute_modified_z_score(2000, 1000, 1000)
    assert score == pytest.approx(0.6745, abs=1e-6)

    # Zero MAD raises ValueError (division by zero protection)
    with pytest.raises(ValueError, match="raw MAD is 0"):
        compute_modified_z_score(2000, 1000, 0)


def test_is_potential_outlier_strict_threshold_boundary():
    """
    CRITICAL REQUIREMENT:
    The threshold is strictly abs(score) > 3.5.
    A score of exactly 3.5 or -3.5 must NOT be flagged.
    """
    assert is_potential_outlier(3.5) is False
    assert is_potential_outlier(-3.5) is False
    assert is_potential_outlier(0.0) is False
    assert is_potential_outlier(3.499999) is False
    assert is_potential_outlier(-3.499999) is False

    # Strictly greater than 3.5
    assert is_potential_outlier(3.500001) is True
    assert is_potential_outlier(-3.500001) is True
    assert is_potential_outlier(4.0) is True
    assert is_potential_outlier(-10.5) is True


# ============================================================================
# Section 3: Potential-Outlier Screening Tests (detect_potential_outliers)
# ============================================================================

@pytest.fixture
def outlier_screening_records() -> list[dict]:
    """
    Comprehensive dataset testing all screening guardrails:
    1. Category 'Dining': 5 transactions with 1 extreme amount.
       Amounts: [2000, 2500, 2500, 3000, 35000]
       - median = 2500
       - deviations: |2000-2500|=500, |2500-2500|=0, |2500-2500|=0, |3000-2500|=500, |35000-2500|=32500
       - sorted deviations: [0, 0, 500, 500, 32500] -> raw MAD = 500
       - 35000 score: 0.6745 * (35000 - 2500) / 500 = 0.6745 * 32500 / 500 = 43.8425 > 3.5 -> FLAGGED!
       - 2000 score: 0.6745 * -500 / 500 = -0.6745 -> NOT FLAGGED.

    2. Category 'Groceries': 5 transactions with identical amounts (zero MAD).
       Amounts: [4000, 4000, 4000, 4000, 4000]
       - median = 4000, raw MAD = 0 -> NOT_EVALUATED_ZERO_MAD

    3. Category 'Subscriptions': 3 transactions (insufficient data).
       Amounts: [500, 600, 700]
       - count = 3 < 5 -> NOT_EVALUATED_INSUFFICIENT_DATA

    4. Category 'Transfer': 5 DEBIT transactions (transfers excluded from screening).
       - Must NOT be screened or evaluated as expense outliers.

    5. Category 'Income': 5 CREDIT transactions (credits excluded from screening).
       - Must NOT be screened or evaluated as expense outliers.
    """
    records = []
    # 1. Dining (5 transactions)
    for idx, amt in enumerate([2000, 2500, 2500, 3000, 35000], start=1):
        records.append({
            "transaction_date": f"2026-10-0{idx}",
            "description": f"DINING MEAL {idx}",
            "normalized_description": f"dining meal {idx}",
            "transaction_type": "DEBIT",
            "amount_paise": amt,
            "category": "Dining",
            "rule_id": "R_DINING",
        })

    # 2. Groceries (5 transactions, identical amounts)
    for idx, amt in enumerate([4000, 4000, 4000, 4000, 4000], start=6):
        records.append({
            "transaction_date": f"2026-10-0{idx}",
            "description": f"GROCERY PURCHASE {idx}",
            "normalized_description": f"grocery purchase {idx}",
            "transaction_type": "DEBIT",
            "amount_paise": amt,
            "category": "Groceries",
            "rule_id": "R_GROCERIES",
        })

    # 3. Subscriptions (3 transactions)
    for idx, amt in enumerate([500, 600, 700], start=11):
        records.append({
            "transaction_date": f"2026-10-{idx}",
            "description": f"SUB SERVICE {idx}",
            "normalized_description": f"sub service {idx}",
            "transaction_type": "DEBIT",
            "amount_paise": amt,
            "category": "Subscriptions",
            "rule_id": "R_SUBSCRIPTION",
        })

    # 4. Transfers (5 transactions)
    for idx, amt in enumerate([50000, 60000, 70000, 80000, 90000], start=14):
        records.append({
            "transaction_date": f"2026-10-{idx}",
            "description": f"BANK TRANSFER {idx}",
            "normalized_description": f"bank transfer {idx}",
            "transaction_type": "DEBIT",
            "amount_paise": amt,
            "category": "Transfer",
            "rule_id": "R_TRANSFER",
        })

    # 5. Income (5 transactions, CREDIT)
    for idx, amt in enumerate([100000, 100000, 100000, 100000, 100000], start=19):
        records.append({
            "transaction_date": f"2026-10-{idx}",
            "description": f"CLIENT PAYMENT {idx}",
            "normalized_description": f"client payment {idx}",
            "transaction_type": "CREDIT",
            "amount_paise": amt,
            "category": "Income",
            "rule_id": "R_INCOME",
        })

    return records


def test_detect_potential_outliers_flagged_and_guardrails(db_path, outlier_screening_records):
    """Test outlier screening accurately flags extreme expenses and returns explicit statuses."""
    replace_transactions(db_path, outlier_screening_records)

    results = detect_potential_outliers(db_path)

    # 1. Flagged potential outliers: exactly 1 transaction (the 35000 paise Dining transaction)
    flagged = results["potential_outliers"]
    assert len(flagged) == 1

    outlier = flagged[0]
    assert outlier["category"] == "Dining"
    assert outlier["description"] == "DINING MEAL 5"
    assert outlier["amount_paise"] == 35000
    assert outlier["modified_z_score"] == pytest.approx(43.8425, abs=1e-3)
    assert abs(outlier["modified_z_score"]) > 3.5

    # Cautious language check: must say 'potential outlier', never 'fraud'
    assert "potential outlier" in outlier["explanation"].lower()
    assert "fraud" not in outlier["explanation"].lower()

    # Normal transactions in Dining (2000, 2500, 3000) are NOT flagged
    flagged_amounts = [item["amount_paise"] for item in flagged]
    assert 2000 not in flagged_amounts
    assert 2500 not in flagged_amounts
    assert 3000 not in flagged_amounts

    # 2. Not-evaluated categories: exactly 2 categories (Groceries and Subscriptions)
    not_eval = {item["category"]: item for item in results["not_evaluated"]}
    assert len(not_eval) == 2

    # Groceries: zero MAD
    assert not_eval["Groceries"]["status"] == STATUS_ZERO_MAD
    assert not_eval["Groceries"]["transaction_count"] == 5

    # Subscriptions: insufficient data (< 5 transactions)
    assert not_eval["Subscriptions"]["status"] == STATUS_INSUFFICIENT_DATA
    assert not_eval["Subscriptions"]["transaction_count"] == 3

    # Transfers and Income must NOT appear in not_evaluated or potential_outliers
    assert "Transfer" not in not_eval
    assert "Income" not in not_eval


def test_outlier_screening_exact_boundary_conditions(db_path):
    """
    CRITICAL TEST FOR EXACT THRESHOLD:
    Use a mathematically exact dataset where:
    - median = 10,000 paise
    - raw MAD = 6,745 paise
    - candidate 1 (45,000 paise): score = 0.6745 * (45000 - 10000) / 6745 = 3.5 EXACTLY.
      Rule strictly requires abs(score) > 3.5, so 45,000 must NOT be flagged.
    - candidate 2 (45,001 paise): score = 0.6745 * (45001 - 10000) / 6745 = 3.5001 > 3.5.
      This MUST be flagged.
    """
    # Dataset A: Exact 3.5 score -> NOT flagged
    exact_boundary_records = [
        {"transaction_date": "2026-10-01", "description": "T1", "normalized_description": "t1", "transaction_type": "DEBIT", "amount_paise": 3255, "category": "Boundary", "rule_id": "R_B"},
        {"transaction_date": "2026-10-02", "description": "T2", "normalized_description": "t2", "transaction_type": "DEBIT", "amount_paise": 10000, "category": "Boundary", "rule_id": "R_B"},
        {"transaction_date": "2026-10-03", "description": "T3", "normalized_description": "t3", "transaction_type": "DEBIT", "amount_paise": 10000, "category": "Boundary", "rule_id": "R_B"},
        {"transaction_date": "2026-10-04", "description": "T4", "normalized_description": "t4", "transaction_type": "DEBIT", "amount_paise": 16745, "category": "Boundary", "rule_id": "R_B"},
        {"transaction_date": "2026-10-05", "description": "T5", "normalized_description": "t5", "transaction_type": "DEBIT", "amount_paise": 45000, "category": "Boundary", "rule_id": "R_B"},
    ]
    replace_transactions(db_path, exact_boundary_records)
    res_a = detect_potential_outliers(db_path)
    # Score is 3.5 exactly, not > 3.5: MUST NOT be flagged!
    assert len(res_a["potential_outliers"]) == 0
    assert len(res_a["not_evaluated"]) == 0

    # Dataset B: 45,001 paise (just 1 paise more) -> score = 3.5001 > 3.5 -> FLAGGED!
    over_boundary_records = [
        {"transaction_date": "2026-10-01", "description": "T1", "normalized_description": "t1", "transaction_type": "DEBIT", "amount_paise": 3255, "category": "Boundary", "rule_id": "R_B"},
        {"transaction_date": "2026-10-02", "description": "T2", "normalized_description": "t2", "transaction_type": "DEBIT", "amount_paise": 10000, "category": "Boundary", "rule_id": "R_B"},
        {"transaction_date": "2026-10-03", "description": "T3", "normalized_description": "t3", "transaction_type": "DEBIT", "amount_paise": 10000, "category": "Boundary", "rule_id": "R_B"},
        {"transaction_date": "2026-10-04", "description": "T4", "normalized_description": "t4", "transaction_type": "DEBIT", "amount_paise": 16745, "category": "Boundary", "rule_id": "R_B"},
        {"transaction_date": "2026-10-05", "description": "T5", "normalized_description": "t5", "transaction_type": "DEBIT", "amount_paise": 45001, "category": "Boundary", "rule_id": "R_B"},
    ]
    replace_transactions(db_path, over_boundary_records)
    res_b = detect_potential_outliers(db_path)
    assert len(res_b["potential_outliers"]) == 1
    assert res_b["potential_outliers"][0]["amount_paise"] == 45001
    assert res_b["potential_outliers"][0]["modified_z_score"] > 3.5


def test_outlier_screening_independent_category_baselines(db_path):
    """
    Test that each category is evaluated on its own baseline.
    An extreme expense in 'Transport' must NOT influence the baseline or evaluation of 'Dining'.
    """
    records = [
        # Dining: 5 normal expenses [1000, 1100, 1200, 1300, 1400]
        {"transaction_date": "2026-10-01", "description": "D1", "normalized_description": "d1", "transaction_type": "DEBIT", "amount_paise": 1000, "category": "Dining", "rule_id": "R_D"},
        {"transaction_date": "2026-10-02", "description": "D2", "normalized_description": "d2", "transaction_type": "DEBIT", "amount_paise": 1100, "category": "Dining", "rule_id": "R_D"},
        {"transaction_date": "2026-10-03", "description": "D3", "normalized_description": "d3", "transaction_type": "DEBIT", "amount_paise": 1200, "category": "Dining", "rule_id": "R_D"},
        {"transaction_date": "2026-10-04", "description": "D4", "normalized_description": "d4", "transaction_type": "DEBIT", "amount_paise": 1300, "category": "Dining", "rule_id": "R_D"},
        {"transaction_date": "2026-10-05", "description": "D5", "normalized_description": "d5", "transaction_type": "DEBIT", "amount_paise": 1400, "category": "Dining", "rule_id": "R_D"},

        # Transport: 5 expenses with non-zero MAD (median=2000, MAD=500) and 1 massive outlier
        {"transaction_date": "2026-10-01", "description": "T1", "normalized_description": "t1", "transaction_type": "DEBIT", "amount_paise": 1000, "category": "Transport", "rule_id": "R_T"},
        {"transaction_date": "2026-10-02", "description": "T2", "normalized_description": "t2", "transaction_type": "DEBIT", "amount_paise": 1500, "category": "Transport", "rule_id": "R_T"},
        {"transaction_date": "2026-10-03", "description": "T3", "normalized_description": "t3", "transaction_type": "DEBIT", "amount_paise": 2000, "category": "Transport", "rule_id": "R_T"},
        {"transaction_date": "2026-10-04", "description": "T4", "normalized_description": "t4", "transaction_type": "DEBIT", "amount_paise": 2500, "category": "Transport", "rule_id": "R_T"},
        {"transaction_date": "2026-10-05", "description": "T5", "normalized_description": "t5", "transaction_type": "DEBIT", "amount_paise": 500000, "category": "Transport", "rule_id": "R_T"},
    ]
    replace_transactions(db_path, records)

    results = detect_potential_outliers(db_path)

    # Only Transport has an outlier
    flagged = results["potential_outliers"]
    assert len(flagged) == 1
    assert flagged[0]["category"] == "Transport"
    assert flagged[0]["amount_paise"] == 500000

    # Dining has 0 outliers and is NOT in not_evaluated (it had 5 txs and nonzero MAD)
    assert not any(item["category"] == "Dining" for item in results["not_evaluated"])


def test_detect_potential_outliers_empty_database(db_path):
    """Test detect_potential_outliers on an initialized but empty database."""
    initialize_database(db_path)

    results = detect_potential_outliers(db_path)
    assert results["potential_outliers"] == []
    assert results["not_evaluated"] == []


def test_detect_potential_outliers_nonexistent_database(tmp_path):
    """Test detect_potential_outliers on a nonexistent database path."""
    nonexistent = tmp_path / "nonexistent.db"

    results = detect_potential_outliers(nonexistent)
    assert results["potential_outliers"] == []
    assert results["not_evaluated"] == []
