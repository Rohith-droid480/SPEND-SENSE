"""
SpendSense — CLI Entry Point and Pipeline Orchestration.

This module implements Milestone 5:
1. End-to-end orchestration connecting data processing, categorization,
   atomic storage, SQL summaries, and potential-outlier screening.
2. Safe database preservation:
   - Does NOT touch or replace the database if input CSV is missing,
     unreadable, structurally invalid, or contains zero accepted records.
   - Preserves previous valid datasets on any failure.
3. Clean, beginner-readable terminal reporting:
   - File and import status (accepted / rejected counts).
   - Rejection reasons with record and line numbers (no dumping full row data).
   - Ordinary expenses total and category breakdown (excluding transfers).
   - Credits total and category breakdown (separate refunds, not netted).
   - Transfers summary (debits, credits, excluded from expense baselines).
   - Flagged potential outliers (Modified Z-score strictly > 3.5, never 'fraud').
   - Not-evaluated category statuses (insufficient data, zero MAD).
   - Exact INR display formatting (e.g. 1050 paise -> '₹10.50') without float conversion.
"""

from argparse import ArgumentParser, Namespace
from pathlib import Path
import sqlite3
import sys
from typing import Any

from analysis import calculate_summary, detect_potential_outliers
from categorization import categorize_transaction, normalize_description
from data_processing import CSVFileError, CSVFileNotFoundError, load_and_validate_csv
from storage import replace_transactions

# Ensure UTF-8 stream encoding for rupee symbol ('₹') across platforms
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def format_paise_to_inr(paise: int) -> str:
    """
    Format integer paise to INR currency string without floating-point conversion.

    Examples:
    - 0 -> '₹0.00'
    - 50 -> '₹0.50'
    - 1050 -> '₹10.50'
    - 500000 -> '₹5000.00'
    """
    if isinstance(paise, bool) or not isinstance(paise, int):
        raise TypeError(f"paise must be an int, got {type(paise).__name__}")

    if paise < 0:
        sign = "-"
        abs_paise = abs(paise)
    else:
        sign = ""
        abs_paise = paise

    rupees = abs_paise // 100
    remainder = abs_paise % 100
    return f"{sign}₹{rupees}.{remainder:02d}"


def format_report(
    csv_path: str | Path,
    db_path: str | Path,
    accepted_records: list[dict[str, Any]],
    rejected_records: list[dict[str, Any]],
    summary: dict[str, Any],
    outliers: dict[str, Any],
) -> str:
    """
    Construct a clean, human-readable terminal report summarizing the pipeline results.
    """
    total_considered = len(accepted_records) + len(rejected_records)
    lines: list[str] = []

    lines.append("=" * 70)
    lines.append("SPENDSENSE — TRANSACTION & ANOMALY REPORT")
    lines.append("=" * 70)
    lines.append(f"Input File: {csv_path}")
    lines.append(f"Database:   {db_path}")
    lines.append(
        f"Import:     SUCCESS ({len(accepted_records)} accepted, {len(rejected_records)} rejected)"
    )

    # 1. Import Summary Section
    lines.append("")
    lines.append("-" * 70)
    lines.append("IMPORT SUMMARY")
    lines.append("-" * 70)
    lines.append(f"Total rows considered: {total_considered}")
    lines.append(f"Accepted records:      {len(accepted_records)}")
    lines.append(f"Rejected rows:         {len(rejected_records)}")

    if rejected_records:
        lines.append("")
        lines.append("Rejection details:")
        for rej in rejected_records:
            lines.append(
                f"  - Record {rej['record_number']} (Line {rej['line_number']}): {rej['reason']}"
            )
    else:
        lines.append("")
        lines.append("Rejection details: None. All rows passed validation.")

    # 2. Ordinary Expenses Summary
    lines.append("")
    lines.append("-" * 70)
    lines.append("EXPENSE SUMMARY (Ordinary Debits)")
    lines.append("-" * 70)
    exp_total = summary.get("total_expenses_paise", 0)
    lines.append(f"Total Expenses: {format_paise_to_inr(exp_total)}")

    exp_cats = summary.get("expenses_by_category", [])
    if exp_cats:
        lines.append("")
        lines.append("By Category:")
        for cat in exp_cats:
            c_name = cat["category"]
            c_tot = format_paise_to_inr(cat["total_paise"])
            c_cnt = cat["transaction_count"]
            lines.append(f"  - {c_name:<16}: {c_tot:>10} ({c_cnt} transaction{'s' if c_cnt != 1 else ''})")
    else:
        lines.append("By Category: None.")

    # 3. Credits Summary
    lines.append("")
    lines.append("-" * 70)
    lines.append("CREDIT SUMMARY")
    lines.append("-" * 70)
    credit_total = summary.get("total_credits_paise", 0)
    lines.append(f"Total Credits: {format_paise_to_inr(credit_total)}")

    credit_cats = summary.get("credits_by_category", [])
    if credit_cats:
        lines.append("")
        lines.append("By Category:")
        for cat in credit_cats:
            c_name = cat["category"]
            c_tot = format_paise_to_inr(cat["total_paise"])
            c_cnt = cat["transaction_count"]
            lines.append(f"  - {c_name:<16}: {c_tot:>10} ({c_cnt} transaction{'s' if c_cnt != 1 else ''})")
    else:
        lines.append("By Category: None.")
    lines.append("")
    lines.append("* Note: Refunds are reported separately as credits and not netted against purchases.")

    # 4. Transfers Summary
    lines.append("")
    lines.append("-" * 70)
    lines.append("TRANSFERS SUMMARY")
    lines.append("-" * 70)
    transfers = summary.get("transfers", {})
    t_tot = format_paise_to_inr(transfers.get("total_paise", 0))
    t_cnt = transfers.get("transaction_count", 0)
    lines.append(f"Total Transfers: {t_tot} ({t_cnt} transaction{'s' if t_cnt != 1 else ''})")

    t_types = transfers.get("by_type", [])
    if t_types:
        lines.append("")
        lines.append("By Transaction Type:")
        for item in t_types:
            tt_name = item["transaction_type"]
            tt_tot = format_paise_to_inr(item["total_paise"])
            tt_cnt = item["transaction_count"]
            lines.append(f"  - {tt_name:<16}: {tt_tot:>10} ({tt_cnt} transaction{'s' if tt_cnt != 1 else ''})")
    else:
        lines.append("By Transaction Type: None.")
    lines.append("")
    lines.append("* Note: Transfers are tracked separately and excluded from ordinary expenses.")

    # 5. Potential Outlier Screening
    lines.append("")
    lines.append("-" * 70)
    lines.append("POTENTIAL OUTLIER SCREENING (Category-Specific Modified Z-Score)")
    lines.append("-" * 70)
    lines.append("Baseline: Eligible DEBITs excluding Transfer (minimum 5 observations per category).")
    lines.append("Threshold: Strictly |Modified Z-Score| > 3.5.")

    flagged = outliers.get("potential_outliers", [])
    lines.append("")
    lines.append("Flagged Potential Outliers:")
    if flagged:
        for item in flagged:
            item_amt = format_paise_to_inr(item["amount_paise"])
            lines.append(
                f"  - [ID {item['id']}] {item['transaction_date']} | {item['category']} | {item['description']}"
            )
            lines.append(
                f"    Amount: {item_amt} | Modified Z-Score: {item['modified_z_score']:.2f}"
            )
            lines.append(f"    Explanation: {item['explanation']}")
    else:
        lines.append("  None. No eligible debit expenses strictly exceeded the threshold.")

    not_eval = outliers.get("not_evaluated", [])
    lines.append("")
    lines.append("Categories Not Evaluated:")
    if not_eval:
        for item in not_eval:
            c_name = item["category"]
            c_cnt = item["transaction_count"]
            c_status = item["status"]
            c_reason = item["reason"]
            lines.append(
                f"  - {c_name} ({c_cnt} transaction{'s' if c_cnt != 1 else ''}): {c_status} — {c_reason}"
            )
    else:
        lines.append("  None. All evaluated categories had sufficient observations and non-zero MAD.")

    lines.append("=" * 70)
    return "\n".join(lines)


def run_pipeline(csv_path: str | Path, db_path: str | Path = "spendsense.db") -> int:
    """
    Execute the SpendSense end-to-end pipeline:
    1. Read and validate CSV.
    2. Check that at least one accepted row exists (preserve DB if 0 accepted).
    3. Categorize accepted records.
    4. Atomically replace database records.
    5. Run SQL summaries and outlier screening.
    6. Print report to stdout.

    Returns:
    - 0 on success.
    - 1 on error (file failure, 0 accepted rows, database error).
    """
    # Step 1: Read and validate CSV input
    try:
        accepted_records, rejected_records = load_and_validate_csv(csv_path)
    except CSVFileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except CSVFileError as e:
        print(f"Error: Invalid CSV file: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"Error: Could not read CSV file: {e}", file=sys.stderr)
        return 1

    # Step 2: Ensure at least one accepted row exists before modifying database
    if not accepted_records:
        print(
            f"Error: CSV import failed: No valid records found in '{csv_path}'.",
            file=sys.stderr,
        )
        if rejected_records:
            print(
                f"All {len(rejected_records)} row(s) were rejected. Prior database preserved.",
                file=sys.stderr,
            )
            print("Rejection reasons:", file=sys.stderr)
            for rej in rejected_records:
                print(
                    f"  - Record {rej['record_number']} (Line {rej['line_number']}): {rej['reason']}",
                    file=sys.stderr,
                )
        return 1

    # Step 3: Categorize accepted records and prepare storage dicts
    storage_records: list[dict[str, Any]] = []
    for record in accepted_records:
        category, rule_id = categorize_transaction(
            record["description"], record["transaction_type"]
        )
        norm_desc = normalize_description(record["description"])
        storage_records.append(
            {
                "transaction_date": record["transaction_date"],
                "description": record["description"],
                "normalized_description": norm_desc,
                "transaction_type": record["transaction_type"],
                "amount_paise": record["amount_paise"],
                "category": category,
                "rule_id": rule_id,
            }
        )

    # Step 4: Atomically replace the database dataset
    try:
        replace_transactions(db_path, storage_records)
    except (ValueError, sqlite3.Error, OverflowError) as e:
        print(
            f"Error: Database replacement failed: {e}. Prior database preserved.",
            file=sys.stderr,
        )
        return 1

    # Step 5: Calculate SQL summaries and screen potential outliers
    try:
        summary = calculate_summary(db_path)
        outliers = detect_potential_outliers(db_path)
    except Exception as e:
        print(f"Error: Analysis calculation failed: {e}", file=sys.stderr)
        return 1

    # Step 6: Print terminal report
    report_text = format_report(
        csv_path=csv_path,
        db_path=db_path,
        accepted_records=accepted_records,
        rejected_records=rejected_records,
        summary=summary,
        outliers=outliers,
    )
    print(report_text)
    return 0


def parse_args(argv: list[str] | None = None) -> Namespace:
    """Parse command line arguments."""
    parser = ArgumentParser(
        prog="spendsense",
        description="SpendSense — Expense Pattern & Anomaly Detector",
    )
    parser.add_argument(
        "csv_path",
        help="Path to the transaction CSV file to import and analyze.",
    )
    parser.add_argument(
        "--db",
        dest="db_path",
        default="spendsense.db",
        help="Path to the SQLite database file (default: spendsense.db).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Parses arguments and runs the pipeline."""
    try:
        args = parse_args(argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 2

    return run_pipeline(csv_path=args.csv_path, db_path=args.db_path)


if __name__ == "__main__":
    sys.exit(main())
