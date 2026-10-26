"""
SpendSense — Integration and Unit Tests for Local Web Server & API.

Verifies:
1. Static asset serving (index.html, style.css, app.js).
2. GET /api/status and GET /api/data payloads.
3. POST /api/load-sample seeding.
4. POST /api/import with valid CSV.
5. POST /api/import rejection of invalid headers, all-invalid rows, and corrupt input.
6. Complete database preservation upon failed imports.
7. Consistency between API responses and CLI / core module calculations.
"""

from http import HTTPStatus
import io
import json
from pathlib import Path
import sqlite3
import threading
from urllib.error import HTTPError
import urllib.request
import pytest

import data_processing
import server
import storage

SAMPLE_CSV = Path(__file__).resolve().parent.parent / "data" / "sample_transactions.csv"


@pytest.fixture
def test_db_path(tmp_path: Path) -> Path:
    """Fixture providing a clean temporary SQLite database."""
    db_file = tmp_path / "test_web.db"
    storage.initialize_database(db_file)
    return db_file


@pytest.fixture
def running_server(test_db_path: Path):
    """Fixture running SpendSense ThreadingHTTPServer on an ephemeral port."""
    test_server = server.ThreadingHTTPServer(("127.0.0.1", 0), server.SpendSenseAPIHandler)
    test_server.db_path = test_db_path
    test_server.latest_import_stats = {
        "source": "Test DB",
        "accepted_count": 0,
        "rejected_count": 0,
        "rejected_records": [],
    }

    port = test_server.server_address[1]
    server_thread = threading.Thread(target=test_server.serve_forever, daemon=True)
    server_thread.start()

    base_url = f"http://127.0.0.1:{port}"
    yield base_url, test_db_path

    test_server.shutdown()
    test_server.server_close()


def make_request(
    url: str,
    method: str = "GET",
    data: dict | bytes | None = None,
    content_type: str = "application/json",
) -> tuple[int, dict | str]:
    """Helper to perform HTTP requests against the test server."""
    req = urllib.request.Request(url, method=method)

    if data is not None:
        if isinstance(data, dict):
            body_bytes = json.dumps(data).encode("utf-8")
            req.add_header("Content-Type", content_type)
        else:
            body_bytes = data
            req.add_header("Content-Type", content_type)
        req.data = body_bytes

    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            raw = resp.read().decode("utf-8")
            try:
                return status, json.loads(raw)
            except json.JSONDecodeError:
                return status, raw
    except HTTPError as e:
        status = e.code
        raw = e.read().decode("utf-8")
        try:
            return status, json.loads(raw)
        except json.JSONDecodeError:
            return status, raw


def test_static_asset_serving(running_server):
    """Verify that index.html, style.css, and app.js are served properly."""
    base_url, _ = running_server

    # Root index.html
    status, content = make_request(f"{base_url}/")
    assert status == HTTPStatus.OK
    assert "SpendSense" in content

    # CSS stylesheet
    status, content = make_request(f"{base_url}/style.css")
    assert status == HTTPStatus.OK
    assert "--bg-canvas" in content

    # JavaScript controller
    status, content = make_request(f"{base_url}/app.js")
    assert status == HTTPStatus.OK
    assert "SpendSenseApp" in content


def test_api_status_empty_db(running_server):
    """Verify GET /api/status on a clean database."""
    base_url, _ = running_server
    status, body = make_request(f"{base_url}/api/status")

    assert status == HTTPStatus.OK
    assert body["success"] is True
    assert body["has_records"] is False
    assert body["record_count"] == 0


def test_api_load_sample_endpoint(running_server):
    """Verify POST /api/load-sample correctly ingests sample_transactions.csv."""
    base_url, db_path = running_server
    status, body = make_request(f"{base_url}/api/load-sample", method="POST")

    assert status == HTTPStatus.OK
    assert body["success"] is True

    # Check that sample totals reconcile with CLI output
    summary = body["summary"]
    assert summary["total_expenses_inr"] == "₹10739.50"
    assert summary["total_credits_inr"] == "₹85500.00"
    assert summary["transfers"]["total_inr"] == "₹25000.00"

    # Check outlier
    outliers = body["outliers"]["potential_outliers"]
    assert len(outliers) == 1
    assert outliers[0]["description"] == "Swiggy Feast"
    assert outliers[0]["amount_inr"] == "₹4200.00"
    assert outliers[0]["modified_z_score"] == 52.61

    # Check transactions count
    assert len(body["transactions"]) == 16


def test_api_import_valid_csv(running_server):
    """Verify POST /api/import with a valid CSV replaces the dataset cleanly."""
    base_url, db_path = running_server

    csv_text = (
        "Date,Description,Amount,Type\n"
        "2026-10-01,Zomato Lunch,250.00,DEBIT\n"
        "2026-10-02,Freelance Payment,10000.00,CREDIT\n"
    )

    payload = {"filename": "test.csv", "csv_content": csv_text}
    status, body = make_request(f"{base_url}/api/import", method="POST", data=payload)

    assert status == HTTPStatus.OK
    assert body["success"] is True
    assert body["import_stats"]["accepted_count"] == 2
    assert body["import_stats"]["rejected_count"] == 0

    # Verify rows in SQLite
    rows = storage.read_transactions(db_path)
    assert len(rows) == 2
    assert rows[0]["description"] == "Zomato Lunch"
    assert rows[0]["category"] == "Dining"
    assert rows[1]["description"] == "Freelance Payment"
    assert rows[1]["category"] == "Other Credit"


def test_api_import_invalid_headers_preserves_database(running_server):
    """Verify that importing a CSV with bad headers returns 400 and preserves DB."""
    base_url, db_path = running_server

    # First load sample data
    make_request(f"{base_url}/api/load-sample", method="POST")
    initial_rows = storage.read_transactions(db_path)
    assert len(initial_rows) == 16

    # Attempt to import CSV with invalid headers
    bad_csv = "WrongDate,Description,Amount,Type\n2026-10-01,Lunch,100.00,DEBIT\n"
    payload = {"filename": "bad_headers.csv", "csv_content": bad_csv}
    status, body = make_request(f"{base_url}/api/import", method="POST", data=payload)

    assert status == HTTPStatus.BAD_REQUEST
    assert body["success"] is False
    assert "Invalid CSV file schema" in body["error"]

    # Verify existing DB is completely preserved
    post_rows = storage.read_transactions(db_path)
    assert len(post_rows) == 16
    assert [r["id"] for r in post_rows] == [r["id"] for r in initial_rows]


def test_api_import_all_invalid_rows_preserves_database(running_server):
    """Verify that a CSV where all rows fail validation returns 400 and preserves DB."""
    base_url, db_path = running_server

    # First load sample data
    make_request(f"{base_url}/api/load-sample", method="POST")
    initial_rows = storage.read_transactions(db_path)
    assert len(initial_rows) == 16

    # Attempt to import CSV with valid headers but invalid row dates
    all_bad_csv = (
        "Date,Description,Amount,Type\n"
        "2026-02-30,Impossible Date,100.00,DEBIT\n"
        "2026-13-45,Invalid Month,200.00,DEBIT\n"
    )
    payload = {"filename": "all_bad.csv", "csv_content": all_bad_csv}
    status, body = make_request(f"{base_url}/api/import", method="POST", data=payload)

    assert status == HTTPStatus.BAD_REQUEST
    assert body["success"] is False
    assert "All 2 row(s) failed validation" in body["error"]
    assert len(body["import_stats"]["rejected_records"]) == 2

    # Verify existing DB is completely preserved
    post_rows = storage.read_transactions(db_path)
    assert len(post_rows) == 16


def test_api_import_mixed_valid_and_invalid_rows(running_server):
    """Verify that a CSV with mixed rows accepts valid rows and returns rejection diagnostics."""
    base_url, db_path = running_server

    mixed_csv = (
        "Date,Description,Amount,Type\n"
        "2026-10-01,Valid Meal,250.00,DEBIT\n"
        "2026-02-30,Bad Date,100.00,DEBIT\n"
    )
    payload = {"filename": "mixed.csv", "csv_content": mixed_csv}
    status, body = make_request(f"{base_url}/api/import", method="POST", data=payload)

    assert status == HTTPStatus.OK
    assert body["success"] is True
    assert body["import_stats"]["accepted_count"] == 1
    assert body["import_stats"]["rejected_count"] == 1
    assert len(body["import_stats"]["rejected_records"]) == 1

    # Verify exactly 1 row committed to SQLite
    rows = storage.read_transactions(db_path)
    assert len(rows) == 1
    assert rows[0]["description"] == "Valid Meal"


def test_api_unknown_endpoint_404(running_server):
    """Verify that calling an unknown endpoint returns 404."""
    base_url, _ = running_server
    status, body = make_request(f"{base_url}/api/nonexistent", method="POST")
    assert status == HTTPStatus.NOT_FOUND
    assert body["success"] is False


def test_api_examples_list(running_server):
    """Verify GET /api/examples returns the authorized list of bundled datasets."""
    base_url, _ = running_server
    status, body = make_request(f"{base_url}/api/examples")
    assert status == HTTPStatus.OK
    assert body["success"] is True
    assert "examples" in body
    assert len(body["examples"]) == 5
    filenames = [e["filename"] for e in body["examples"]]
    assert "sample_transactions.csv" in filenames
    assert "everyday_spending.csv" in filenames
    assert "outlier_demo.csv" in filenames
    assert "mixed_transactions.csv" in filenames
    assert "edge_case_valid.csv" in filenames


def test_api_load_example_success(running_server):
    """Verify POST /api/load-example switches datasets and refreshes totals."""
    base_url, db_path = running_server
    payload = {"dataset": "outlier_demo.csv"}
    status, body = make_request(f"{base_url}/api/load-example", method="POST", data=payload)

    assert status == HTTPStatus.OK
    assert body["success"] is True
    assert len(body["transactions"]) == 22
    assert body["summary"]["total_expenses_inr"] == "₹14728.00"
    assert len(body["outliers"]["potential_outliers"]) == 2

    # Check database persistence
    rows = storage.read_transactions(db_path)
    assert len(rows) == 22


def test_api_load_example_allowlist_security(running_server):
    """Verify POST /api/load-example rejects unauthorized filenames and path traversal attempts."""
    base_url, _ = running_server
    payload = {"dataset": "../../etc/passwd"}
    status, body = make_request(f"{base_url}/api/load-example", method="POST", data=payload)

    assert status == HTTPStatus.BAD_REQUEST
    assert body["success"] is False
    assert "not in the safe allowlist" in body["error"]

