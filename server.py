"""
SpendSense — Local Web Server & API Handler.

Provides a lightweight, standard-library HTTP server that connects the browser UI
to the authoritative SpendSense financial engine:
1. Serves static frontend assets (HTML, CSS, JS) from the 'web/' directory.
2. Provides REST API endpoints:
   - GET  /api/status      : Dataset status and loaded database info
   - GET  /api/data        : Complete financial summaries, transactions, and outliers
   - POST /api/import      : Ingests and validates CSV text, atomically replacing the dataset
   - POST /api/load-sample : Ingests the bundled data/sample_transactions.csv
3. Bound strictly to 127.0.0.1 (localhost) for local privacy and security.
4. Preserves all locked financial rules, integer paise precision, and atomic rollback semantics.
"""

from argparse import ArgumentParser
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
from typing import Any

# Ensure workspace root is in sys.path
WORKSPACE_DIR = Path(__file__).resolve().parent
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

import analysis
import categorization
import data_processing
import main
import storage

WEB_DIR = WORKSPACE_DIR / "web"
SAMPLE_CSV_PATH = WORKSPACE_DIR / "data" / "sample_transactions.csv"
EXAMPLES_DIR = WORKSPACE_DIR / "data" / "examples"

BUNDLED_EXAMPLES: dict[str, dict[str, Any]] = {
    "sample_transactions.csv": {
        "filename": "sample_transactions.csv",
        "name": "Canonical Sample",
        "path": SAMPLE_CSV_PATH,
        "description": "Standard 16-transaction reference dataset featuring 1 outlier (Swiggy Feast ₹4,200) and insufficient-data guardrails.",
        "records": 16,
    },
    "everyday_spending.csv": {
        "filename": "everyday_spending.csv",
        "name": "Everyday Spending",
        "path": EXAMPLES_DIR / "everyday_spending.csv",
        "description": "Realistic monthly spending (29 rows) across Dining, Groceries, Transport, Subscriptions with 2 fuel outliers.",
        "records": 29,
    },
    "outlier_demo.csv": {
        "filename": "outlier_demo.csv",
        "name": "Outlier & Guardrails Demo",
        "path": EXAMPLES_DIR / "outlier_demo.csv",
        "description": "22 rows demonstrating clear N >= 5 outliers in Dining & Transport, plus the strict NOT_EVALUATED_ZERO_MAD guardrail.",
        "records": 22,
    },
    "mixed_transactions.csv": {
        "filename": "mixed_transactions.csv",
        "name": "Mixed Transactions & Transfers",
        "path": EXAMPLES_DIR / "mixed_transactions.csv",
        "description": "14 rows with debits, salary credit, refund (separate, not netted), and account transfers (excluded from expense baseline).",
        "records": 14,
    },
    "edge_case_valid.csv": {
        "filename": "edge_case_valid.csv",
        "name": "Valid Edge Cases & Decimals",
        "path": EXAMPLES_DIR / "edge_case_valid.csv",
        "description": "8 rows testing exact trailing zeros (.00, .50), leap year dates (2024-02-29), and mixed case sensitivity.",
        "records": 8,
    },
}


class SpendSenseAPIHandler(SimpleHTTPRequestHandler):
    """HTTP Request Handler providing static asset serving and SpendSense JSON APIs."""

    def __init__(self, *args, directory: str | None = None, **kwargs) -> None:
        # Serve static assets strictly from the web/ directory
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    @property
    def db_path(self) -> Path:
        """Retrieve database path from the server instance."""
        return getattr(self.server, "db_path", WORKSPACE_DIR / "spendsense.db")

    @property
    def latest_import_stats(self) -> dict[str, Any]:
        """Retrieve latest import diagnostics from the server instance."""
        return getattr(
            self.server,
            "latest_import_stats",
            {
                "accepted_count": 0,
                "rejected_count": 0,
                "rejected_records": [],
                "source": "None",
            },
        )

    @latest_import_stats.setter
    def latest_import_stats(self, value: dict[str, Any]) -> None:
        self.server.latest_import_stats = value

    def send_json(self, status: int, data: dict[str, Any]) -> None:
        """Send a formatted JSON response with security and caching headers."""
        payload = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self) -> None:
        """Handle CORS pre-flight requests."""
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        """Handle GET requests for APIs or static frontend files."""
        parsed_path = self.path.split("?")[0].rstrip("/")

        if parsed_path == "/api/status":
            self.handle_api_status()
            return
        elif parsed_path in ("/api/data", "/api/summary"):
            self.handle_api_data()
            return
        elif parsed_path == "/api/examples":
            self.handle_api_examples()
            return

        # Fallback to serving static files from web/ (index.html, style.css, app.js)
        if self.path == "/" or not self.path:
            self.path = "/index.html"

        super().do_GET()

    def do_POST(self) -> None:
        """Handle POST requests for CSV ingestion and sample data loading."""
        parsed_path = self.path.split("?")[0].rstrip("/")

        if parsed_path == "/api/import":
            self.handle_api_import()
        elif parsed_path == "/api/load-sample":
            self.handle_api_load_sample()
        elif parsed_path == "/api/load-example":
            self.handle_api_load_example()
        else:
            self.send_json(
                HTTPStatus.NOT_FOUND,
                {"success": False, "error": f"Endpoint not found: {self.path}"},
            )

    # --------------------------------------------------------------------------
    # API Implementation Methods
    # --------------------------------------------------------------------------

    def handle_api_status(self) -> None:
        """Return high-level database status and record count."""
        db_exists = self.db_path.exists()
        count = 0
        if db_exists:
            try:
                conn = storage.get_connection(self.db_path)
                count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
                conn.close()
            except Exception:
                count = 0

        self.send_json(
            HTTPStatus.OK,
            {
                "success": True,
                "db_path": str(self.db_path),
                "db_name": self.db_path.name,
                "has_records": count > 0,
                "record_count": count,
                "latest_import": self.latest_import_stats,
            },
        )

    def handle_api_data(self) -> None:
        """Return complete summaries, transactions, and outliers."""
        storage.initialize_database(self.db_path)

        try:
            summary = analysis.calculate_summary(self.db_path)
            outliers = analysis.detect_potential_outliers(self.db_path)
            rows = storage.read_transactions(self.db_path)
        except Exception as e:
            self.send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"success": False, "error": f"Analysis calculation error: {str(e)}"},
            )
            return

        # Format transactions for frontend display with formatted INR currency
        transactions = []
        for r in rows:
            transactions.append(
                {
                    "id": r["id"],
                    "transaction_date": r["transaction_date"],
                    "description": r["description"],
                    "normalized_description": r["normalized_description"],
                    "transaction_type": r["transaction_type"],
                    "amount_paise": r["amount_paise"],
                    "amount_inr": main.format_paise_to_inr(r["amount_paise"]),
                    "category": r["category"],
                    "rule_id": r["rule_id"],
                }
            )

        # Enhance category summary with formatted INR strings and percentages
        total_exp_paise = summary.get("total_expenses_paise", 0)
        expenses_by_cat = []
        for cat in summary.get("expenses_by_category", []):
            paise = cat["total_paise"]
            pct = round((paise / total_exp_paise * 100), 1) if total_exp_paise > 0 else 0.0
            expenses_by_cat.append(
                {
                    "category": cat["category"],
                    "total_paise": paise,
                    "total_inr": main.format_paise_to_inr(paise),
                    "transaction_count": cat["transaction_count"],
                    "percentage": pct,
                }
            )

        credits_by_cat = [
            {
                "category": c["category"],
                "total_paise": c["total_paise"],
                "total_inr": main.format_paise_to_inr(c["total_paise"]),
                "transaction_count": c["transaction_count"],
            }
            for c in summary.get("credits_by_category", [])
        ]

        transfers_by_type = [
            {
                "transaction_type": t["transaction_type"],
                "total_paise": t["total_paise"],
                "total_inr": main.format_paise_to_inr(t["total_paise"]),
                "transaction_count": t["transaction_count"],
            }
            for t in summary.get("transfers", {}).get("by_type", [])
        ]

        # Add formatted currency to potential outliers
        formatted_outliers = []
        for o in outliers.get("potential_outliers", []):
            formatted_outliers.append(
                {
                    "id": o["id"],
                    "transaction_date": o["transaction_date"],
                    "description": o["description"],
                    "category": o["category"],
                    "amount_paise": o["amount_paise"],
                    "amount_inr": main.format_paise_to_inr(o["amount_paise"]),
                    "modified_z_score": round(o["modified_z_score"], 2),
                    "explanation": o["explanation"],
                }
            )

        response_data = {
            "success": True,
            "db_name": self.db_path.name,
            "import_stats": self.latest_import_stats,
            "summary": {
                "total_expenses_paise": total_exp_paise,
                "total_expenses_inr": main.format_paise_to_inr(total_exp_paise),
                "expenses_by_category": expenses_by_cat,
                "total_credits_paise": summary.get("total_credits_paise", 0),
                "total_credits_inr": main.format_paise_to_inr(
                    summary.get("total_credits_paise", 0)
                ),
                "credits_by_category": credits_by_cat,
                "transfers": {
                    "total_paise": summary.get("transfers", {}).get("total_paise", 0),
                    "total_inr": main.format_paise_to_inr(
                        summary.get("transfers", {}).get("total_paise", 0)
                    ),
                    "transaction_count": summary.get("transfers", {}).get(
                        "transaction_count", 0
                    ),
                    "by_type": transfers_by_type,
                },
            },
            "outliers": {
                "potential_outliers": formatted_outliers,
                "not_evaluated": outliers.get("not_evaluated", []),
            },
            "transactions": transactions,
        }

        self.send_json(HTTPStatus.OK, response_data)

    def handle_api_examples(self) -> None:
        """Return the allowlist of bundled synthetic example CSV datasets."""
        examples_list = [
            {
                "id": key,
                "filename": val["filename"],
                "name": val["name"],
                "description": val["description"],
                "records": val["records"],
                "exists": val["path"].exists(),
            }
            for key, val in BUNDLED_EXAMPLES.items()
        ]
        self.send_json(HTTPStatus.OK, {"success": True, "examples": examples_list})

    def handle_api_load_sample(self) -> None:
        """Load bundled synthetic sample dataset into the database."""
        self._load_bundled_named_example("sample_transactions.csv")

    def handle_api_load_example(self) -> None:
        """Load an authorized bundled example dataset from the safe allowlist."""
        content_length = int(self.headers.get("Content-Length", 0))
        target_name = ""
        if content_length > 0:
            try:
                body = json.loads(self.rfile.read(content_length).decode("utf-8"))
                target_name = body.get("dataset") or body.get("example_name") or body.get("name") or ""
            except Exception:
                target_name = ""

        if not target_name:
            target_name = "sample_transactions.csv"

        # Safe Allowlist Validation: strictly prohibit arbitrary path traversal
        if target_name not in BUNDLED_EXAMPLES:
            allowed_names = list(BUNDLED_EXAMPLES.keys())
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                {
                    "success": False,
                    "error": f"Dataset '{target_name}' is not in the safe allowlist of bundled examples.",
                    "allowed_examples": allowed_names,
                },
            )
            return

        self._load_bundled_named_example(target_name)

    def _load_bundled_named_example(self, target_name: str) -> None:
        """Helper to safely ingest a verified bundled example dataset."""
        example_entry = BUNDLED_EXAMPLES.get(target_name)
        if not example_entry or not example_entry["path"].exists():
            self.send_json(
                HTTPStatus.NOT_FOUND,
                {"success": False, "error": f"Bundled example '{target_name}' not found on server."},
            )
            return

        example_path = example_entry["path"]
        success, err_msg, stats = self._execute_csv_ingestion(
            example_path, source_label=f"data/{example_path.name}"
        )
        if not success:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                {"success": False, "error": err_msg, "import_stats": stats},
            )
            return

        self.latest_import_stats = stats
        self.handle_api_data()

    def handle_api_import(self) -> None:
        """Handle uploaded CSV content, validate it, and atomically replace the database."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except (ValueError, TypeError):
            content_length = 0

        if content_length <= 0:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                {"success": False, "error": "Empty request body. Please provide CSV data."},
            )
            return

        raw_body = self.rfile.read(content_length)
        content_type = self.headers.get("Content-Type", "")

        csv_text = ""
        source_label = "Uploaded File"

        if "application/json" in content_type:
            try:
                parsed_json = json.loads(raw_body.decode("utf-8"))
                csv_text = parsed_json.get("csv_content", "")
                source_label = parsed_json.get("filename", "Uploaded CSV")
            except Exception as e:
                self.send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"success": False, "error": f"Invalid JSON payload: {str(e)}"},
                )
                return
        elif "multipart/form-data" in content_type:
            # Simple standard-library extraction for single file upload
            boundary = content_type.split("boundary=")[-1].encode("utf-8")
            parts = raw_body.split(b"--" + boundary)
            for part in parts:
                if b'filename="' in part:
                    # Extract filename if available
                    try:
                        header_part, file_data = part.split(b"\r\n\r\n", 1)
                        # Trim trailing \r\n--
                        file_data = file_data.rstrip(b"\r\n--")
                        csv_text = file_data.decode("utf-8-sig")
                        source_label = "Uploaded CSV"
                        break
                    except Exception as e:
                        self.send_json(
                            HTTPStatus.BAD_REQUEST,
                            {"success": False, "error": f"Error parsing uploaded file: {str(e)}"},
                        )
                        return
        else:
            # Assume raw CSV text
            try:
                csv_text = raw_body.decode("utf-8-sig")
            except UnicodeDecodeError:
                self.send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"success": False, "error": "Invalid file encoding: CSV must be valid UTF-8."},
                )
                return

        if not csv_text.strip():
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                {
                    "success": False,
                    "error": "CSV content is empty. Please provide valid transaction records.",
                },
            )
            return

        # Write to temporary file for exact validation by data_processing.py
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", encoding="utf-8", delete=False
        ) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write(csv_text)

        try:
            success, err_msg, stats = self._execute_csv_ingestion(
                tmp_path, source_label=source_label
            )
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass

        if not success:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                {"success": False, "error": err_msg, "import_stats": stats},
            )
            return

        self.latest_import_stats = stats
        self.handle_api_data()

    def _execute_csv_ingestion(
        self, csv_file_path: Path, source_label: str
    ) -> tuple[bool, str, dict[str, Any]]:
        """
        Run the exact SpendSense ingestion pipeline:
        1. load_and_validate_csv
        2. Verify accepted_records > 0
        3. categorize_transaction
        4. replace_transactions (atomic swap with rollback)
        """
        try:
            accepted_records, rejected_records = data_processing.load_and_validate_csv(
                csv_file_path
            )
        except data_processing.CSVFileNotFoundError as e:
            return False, str(e), {"source": source_label, "accepted_count": 0, "rejected_count": 0, "rejected_records": []}
        except data_processing.CSVFileError as e:
            return False, f"Invalid CSV file schema: {e}", {"source": source_label, "accepted_count": 0, "rejected_count": 0, "rejected_records": []}
        except Exception as e:
            return False, f"Could not parse CSV: {e}", {"source": source_label, "accepted_count": 0, "rejected_count": 0, "rejected_records": []}

        stats = {
            "source": source_label,
            "accepted_count": len(accepted_records),
            "rejected_count": len(rejected_records),
            "rejected_records": rejected_records,
        }

        if not accepted_records:
            return (
                False,
                f"No valid records found. All {len(rejected_records)} row(s) failed validation. Prior database preserved.",
                stats,
            )

        storage_records: list[dict[str, Any]] = []
        for record in accepted_records:
            category, rule_id = categorization.categorize_transaction(
                record["description"], record["transaction_type"]
            )
            norm_desc = categorization.normalize_description(record["description"])
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

        try:
            storage.replace_transactions(self.db_path, storage_records)
        except (ValueError, sqlite3.Error, OverflowError) as e:
            return False, f"Database replacement error: {e}. Prior database preserved.", stats

        return True, "", stats


def run_server(
    host: str = "127.0.0.1",
    port: int = 8080,
    db_path: str | Path = "spendsense.db",
    auto_load_sample: bool = True,
) -> None:
    """Initialize database and start the ThreadingHTTPServer."""
    resolved_db = Path(db_path).resolve()
    storage.initialize_database(resolved_db)

    # Automatically seed sample data if database is empty
    conn = storage.get_connection(resolved_db)
    row_count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    conn.close()

    server = ThreadingHTTPServer((host, port), SpendSenseAPIHandler)
    server.db_path = resolved_db
    server.latest_import_stats = {
        "source": "Initial Database",
        "accepted_count": row_count,
        "rejected_count": 0,
        "rejected_records": [],
    }

    if row_count == 0 and auto_load_sample and SAMPLE_CSV_PATH.exists():
        print(f"Database empty. Seeding bundled sample data from {SAMPLE_CSV_PATH.name}...")
        try:
            accepted, rejected = data_processing.load_and_validate_csv(SAMPLE_CSV_PATH)
            storage_records = []
            for record in accepted:
                cat, rule_id = categorization.categorize_transaction(
                    record["description"], record["transaction_type"]
                )
                storage_records.append(
                    {
                        "transaction_date": record["transaction_date"],
                        "description": record["description"],
                        "normalized_description": categorization.normalize_description(
                            record["description"]
                        ),
                        "transaction_type": record["transaction_type"],
                        "amount_paise": record["amount_paise"],
                        "category": cat,
                        "rule_id": rule_id,
                    }
                )
            storage.replace_transactions(resolved_db, storage_records)
            server.latest_import_stats = {
                "source": "Bundled Sample Data",
                "accepted_count": len(accepted),
                "rejected_count": len(rejected),
                "rejected_records": rejected,
            }
            print(f"Sample data loaded: {len(accepted)} records.")
        except Exception as e:
            print(f"Warning: Could not auto-load sample data: {e}")

    url = f"http://{host}:{port}"
    print("=" * 65)
    print(" SPENDSENSE LOCAL WEB SERVER RUNNING")
    print("=" * 65)
    print(f"  URL:      {url}")
    print(f"  Database: {resolved_db}")
    print("  Privacy:  100% Local (127.0.0.1) — No External Calls")
    print("  Controls: Press Ctrl+C in terminal to stop")
    print("=" * 65)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping SpendSense web server cleanly...")
    finally:
        server.server_close()
        print("Server stopped.")


def main_cli() -> None:
    """CLI argument parser for running the server."""
    parser = ArgumentParser(description="SpendSense Local Web Interface Server")
    parser.add_argument("--host", default="127.0.0.1", help="Binding host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    parser.add_argument(
        "--db",
        dest="db_path",
        default="spendsense.db",
        help="SQLite database path (default: spendsense.db)",
    )
    parser.add_argument(
        "--no-sample",
        action="store_true",
        help="Do not automatically seed sample data if database is empty",
    )
    args = parser.parse_args()

    run_server(
        host=args.host,
        port=args.port,
        db_path=args.db_path,
        auto_load_sample=not args.no_sample,
    )


if __name__ == "__main__":
    main_cli()
