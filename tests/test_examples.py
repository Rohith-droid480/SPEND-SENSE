"""
Unit and integration tests for the bundled synthetic example CSV datasets.
Verifies that all bundled examples in data/ and data/examples/ parse cleanly,
match exact expected financial metrics, and exercise outlier guardrails.
"""
from pathlib import Path
import tempfile
import pytest

import data_processing
import categorization
import storage
import analysis


REPO_ROOT = Path(__file__).resolve().parent.parent


def _process_dataset(csv_path: Path):
    accepted, rejected = data_processing.load_and_validate_csv(csv_path)
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)
    try:
        storage.initialize_database(db_path)
        records = []
        for r in accepted:
            cat, rule = categorization.categorize_transaction(r["description"], r["transaction_type"])
            records.append({
                "transaction_date": r["transaction_date"],
                "description": r["description"],
                "normalized_description": categorization.normalize_description(r["description"]),
                "amount_paise": r["amount_paise"],
                "transaction_type": r["transaction_type"],
                "category": cat,
                "rule_id": rule,
            })
        storage.replace_transactions(db_path, records)
        summary = analysis.calculate_summary(db_path)
        outliers = analysis.detect_potential_outliers(db_path)
        return accepted, rejected, summary, outliers
    finally:
        if db_path.exists():
            db_path.unlink()


def test_canonical_sample_transactions():
    p = REPO_ROOT / "data" / "sample_transactions.csv"
    assert p.is_file(), f"Missing canonical sample: {p}"
    accepted, rejected, summary, outliers = _process_dataset(p)

    assert len(accepted) == 16
    assert len(rejected) == 0
    assert summary["total_expenses_paise"] == 1073950  # ₹10,739.50
    assert summary["total_credits_paise"] == 8550000   # ₹85,500.00
    assert summary["transfers"]["total_paise"] == 2500000  # ₹25,000.00

    assert len(outliers["potential_outliers"]) == 1
    assert outliers["potential_outliers"][0]["description"] == "Swiggy Feast"
    assert outliers["potential_outliers"][0]["amount_paise"] == 420000


def test_everyday_spending_dataset():
    p = REPO_ROOT / "data" / "examples" / "everyday_spending.csv"
    assert p.is_file(), f"Missing everyday_spending.csv: {p}"
    accepted, rejected, summary, outliers = _process_dataset(p)

    assert len(accepted) == 29
    assert len(rejected) == 0
    assert summary["total_expenses_paise"] == 1694750  # ₹16,947.50
    assert summary["total_credits_paise"] == 8745000   # ₹87,450.00
    assert summary["transfers"]["total_paise"] == 1700000  # ₹17,000.00

    assert len(outliers["potential_outliers"]) == 2
    outlier_descs = [o["description"] for o in outliers["potential_outliers"]]
    assert "Shell Fuel Refill" in outlier_descs
    assert "Shell Auto Fuel" in outlier_descs


def test_outlier_demo_dataset():
    p = REPO_ROOT / "data" / "examples" / "outlier_demo.csv"
    assert p.is_file(), f"Missing outlier_demo.csv: {p}"
    accepted, rejected, summary, outliers = _process_dataset(p)

    assert len(accepted) == 22
    assert len(rejected) == 0
    assert summary["total_expenses_paise"] == 1472800  # ₹14,728.00
    assert summary["total_credits_paise"] == 9000000   # ₹90,000.00
    assert summary["transfers"]["total_paise"] == 2000000  # ₹20,000.00

    assert len(outliers["potential_outliers"]) == 2
    outlier_descs = [o["description"] for o in outliers["potential_outliers"]]
    assert "Uber Intercity Airport Express" in outlier_descs
    assert "Swiggy Grand Party Catering" in outlier_descs

    # Verify zero-MAD status is exercised for Uncategorized (5 identical 100.00 debit items)
    ne_dict = {ne["category"]: ne["status"] for ne in outliers["not_evaluated"]}
    assert ne_dict.get("Uncategorized") == "NOT_EVALUATED_ZERO_MAD"


def test_mixed_transactions_dataset():
    p = REPO_ROOT / "data" / "examples" / "mixed_transactions.csv"
    assert p.is_file(), f"Missing mixed_transactions.csv: {p}"
    accepted, rejected, summary, outliers = _process_dataset(p)

    assert len(accepted) == 14
    assert len(rejected) == 0
    assert summary["total_expenses_paise"] == 1066900  # ₹10,669.00
    assert summary["total_credits_paise"] == 8162500   # ₹81,625.00
    assert summary["transfers"]["total_paise"] == 5000000  # ₹50,000.00
    assert len(outliers["potential_outliers"]) == 0    # All categories < 5 records


def test_edge_case_valid_dataset():
    p = REPO_ROOT / "data" / "examples" / "edge_case_valid.csv"
    assert p.is_file(), f"Missing edge_case_valid.csv: {p}"
    accepted, rejected, summary, outliers = _process_dataset(p)

    assert len(accepted) == 8
    assert len(rejected) == 0
    assert summary["total_expenses_paise"] == 246576   # ₹2,465.76
    assert summary["total_credits_paise"] == 5002500   # ₹50,025.00
    assert summary["transfers"]["total_paise"] == 500000  # ₹5,000.00
    assert len(outliers["potential_outliers"]) == 0
