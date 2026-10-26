# SpendSense — Expense Pattern & Anomaly Detector

SpendSense is a local personal finance engineering and analytics application built with Python 3.10+ standard-library tooling, SQLite, and a modern vanilla JS/CSS web interface. It validates synthetic personal financial records, applies deterministic rule-based categorization, atomically replaces an embedded SQLite dataset, computes SQL aggregation summaries, and screens eligible expenses for potential statistical outliers using category-specific Modified Z-scores from raw Median Absolute Deviation (MAD).

> [!NOTE]
> **Synthetic Data & Local Privacy:** All sample datasets provided with SpendSense contain purely synthetic demonstration records. SpendSense binds strictly to `127.0.0.1` (localhost), makes zero external network or telemetry calls, and does not connect to real financial accounts or institutions.

---

## Quick Launch: Browser Experience

SpendSense includes an interactive, responsive local web interface featuring real-time dataset switching, dynamic SVG spending charts, search/filter tables, and drag-and-drop CSV ingestion with atomic database replacement.

### 1. Launch the Local Web Application

#### Option A: One-Click Windows Launcher
Double-click the bundled launcher in the repository root:
```text
launch_spendsense.bat
```

#### Option B: Terminal Command
Run the standard-library server from the project root:
```powershell
python server.py --port 8080
```

### 2. Open in Your Browser
Navigate to:
```text
http://127.0.0.1:8080/
```

### 3. How to Stop the Application
Press `Ctrl + C` in the terminal where `server.py` is running, or close the terminal window.

---

## Interactive Browser Features

- **Real-Time Dataset Switcher:** Switch instantly between 5 bundled synthetic datasets in the header dropdown or CSV Ingestion tab. Totals, charts, transactions, and outlier screenings update immediately without a full page reload.
- **Stat Cards Quartet:** Immediate visibility into Ordinary Expenses (eligible debits), Total Credits (income and refunds), Account Transfers (isolated, non-distorting), and Potential Outliers.
- **Dynamic Category Visualizations:** Interactive SVG donut chart and category distribution bars with exact rupee amounts.
- **Searchable & Filterable Ledger:** Filter transactions by category or type (Debit/Credit), search merchant descriptions in real-time, and sort by date or amount.
- **Statistical Outlier & Guardrails Panel:** Detailed cards for flagged transactions ($|\text{Modified Z}| > 3.5$) alongside explainable cards for categories guarded by sample size ($N < 5$) or zero MAD ($\text{MAD} = 0$).
- **CSV Ingestion Drop Zone:** Drag and drop your own CSV statement for instant schema validation and atomic database replacement with full rollback on error.

---

## Bundled Synthetic Datasets

SpendSense includes 5 distinct synthetic datasets inside `data/` and `data/examples/` for demonstration, testing, and edge-case validation:

| Dataset File | Exact Path | Records | Ordinary Expenses | Total Credits | Transfers | Outlier Findings & Guardrails |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Canonical Sample** | `data/sample_transactions.csv` | 16 | ₹10,739.50 | ₹85,500.00 | ₹25,000.00 | 1 Outlier: *Swiggy Feast* (₹4,200.00, $Z = 52.61$). Guardrails: Groceries, Subscriptions, Transport ($N < 5$). |
| **Everyday Spending** | `data/examples/everyday_spending.csv` | 29 | ₹16,947.50 | ₹87,450.00 | ₹17,000.00 | 2 Outliers in Transport: *Shell Fuel Refill* (₹1,500.00, $Z = 8.56$), *Shell Auto Fuel* (₹1,200.00, $Z = 6.43$). |
| **Outlier & Zero-MAD Demo** | `data/examples/outlier_demo.csv` | 22 | ₹14,728.00 | ₹90,000.00 | ₹20,000.00 | 2 Outliers: *Uber Intercity Airport Express* (₹4,200.00, $Z = 135.74$), *Swiggy Grand Party Catering* (₹6,800.00, $Z = 110.28$). Strict guardrail: `NOT_EVALUATED_ZERO_MAD` on Uncategorized. |
| **Mixed & Transfers** | `data/examples/mixed_transactions.csv` | 14 | ₹10,669.00 | ₹81,625.00 | ₹50,000.00 | 0 Outliers (all $N < 5$). Demonstrates separate credit reporting (Salary ₹80k + Refund ₹1,625) and isolated transfers (₹50k). |
| **Edge Cases & Decimals** | `data/examples/edge_case_valid.csv` | 8 | ₹2,465.76 | ₹50,025.00 | ₹5,000.00 | Tests exact trailing decimal zeros (`.00`, `.50`), leap year calendar date (`2024-02-29`), and mixed case normalization. |

---

## Architecture & Data Flow

SpendSense executes as a clean, sequential single-process pipeline without external frameworks:

```text
CSV File (e.g. data/sample_transactions.csv or user upload)
   │
   ▼
1. load_and_validate_csv (data_processing.py)
   ├── File-level check (headers, UTF-8 encoding, non-empty, restkey collision)
   └── Row-level validation (date, description, amount, type)
   │   ├── Accepted Valid Records
   │   └── Rejected Rows + Error Reasons
   ▼
2. to_paise (data_processing.py)
   └── Validates decimal INR amount and converts directly to integer paise
   ▼
3. categorize_transaction & normalize_description (categorization.py)
   └── Applies deterministic priority rules; assigns category and rule_id
   ▼
4. replace_transactions (storage.py)
   └── Atomically replaces SQLite 'transactions' table inside a single transaction
   ▼
5. calculate_summary & detect_potential_outliers (analysis.py)
   ├── SQL aggregations: expenses, category totals, credits, transfers
   └── Python Modified Z-score screening on eligible DEBITs per category
   ▼
6. Output Delivery
   ├── Terminal Report (main.py)
   └── Local REST API & Real-Time Browser Dashboard (server.py + web/)
```

### Module Responsibilities

- **[`main.py`](file:///d:/SPEND%20SENSE/main.py):** CLI entry point and pipeline orchestrator (`run_pipeline`, `main`). Formats terminal reports and coordinates modules without duplicating business logic.
- **[`server.py`](file:///d:/SPEND%20SENSE/server.py):** Local standard-library HTTP server & REST API (`/api/status`, `/api/data`, `/api/examples`, `/api/load-example`, `/api/import`). Serves static web assets and bridges frontend requests to the locked financial engine.
- **[`data_processing.py`](file:///d:/SPEND%20SENSE/data_processing.py):** Input boundary (`load_and_validate_csv`, `to_paise`). Handles strict CSV parsing, UTF-8 decoding protection, calendar date validation, and exact money conversion.
- **[`categorization.py`](file:///d:/SPEND%20SENSE/categorization.py):** Categorization engine (`categorize_transaction`, `normalize_description`). Matches normalized descriptions against ordered rules and assigns stable `rule_id` tags.
- **[`storage.py`](file:///d:/SPEND%20SENSE/storage.py):** SQLite persistence layer (`initialize_database`, `replace_transactions`). Owns database creation, parameterized SQL queries, and atomic dataset replacement.
- **[`analysis.py`](file:///d:/SPEND%20SENSE/analysis.py):** Analytical engine (`calculate_summary`, `detect_potential_outliers`). Executes SQL aggregations and calculates category-specific Modified Z-scores from raw MAD.
- **[`web/`](file:///d:/SPEND%20SENSE/web):** Vanilla HTML5, CSS3, and JavaScript frontend. Zero external frontend frameworks or CDN runtime dependencies.

---

## CSV Input Contract

SpendSense expects a CSV file containing four required header columns in exact order:

```csv
Date,Description,Amount,Type
```

### Column Specifications

| Column | Format / Example | Validation Rules |
| :--- | :--- | :--- |
| `Date` | `2026-10-01` | Required. Strict calendar date in `YYYY-MM-DD` format. Rejects impossible dates (e.g. Feb 30). |
| `Description` | `Zomato Lunch` | Required. Non-empty text string. Preserved in database with original casing. |
| `Amount` | `450.00` | Required. Non-negative, non-zero decimal INR amount with at most two decimal places. Converted directly to integer paise. Never parsed via `float`. |
| `Type` | `DEBIT` or `CREDIT` | Required. Case-insensitive transaction direction (`DEBIT` or `CREDIT`). |

---

## Categorization Hierarchy

Categories are assigned using deterministic, first-match keyword precedence:

1. **`Transfer` (`rule_id: 1`):** Matches `transfer`, `tfr`, `neft`, `rtgs`, `imps`, `upi-transfer` across both DEBIT and CREDIT.
2. **`Income` (`rule_id: 2`):** Matches `salary`, `payroll`, `stipend`, `dividend`, `interest` (CREDIT only).
3. **`Refund` (`rule_id: 3`):** Matches `refund`, `cashback`, `reversal` (CREDIT only).
4. **`Groceries` (`rule_id: 4`):** Matches `grocer`, `supermarket`, `bigbasket`, `blinkit`, `instamart`, `zepto` (DEBIT only).
5. **`Dining` (`rule_id: 5`):** Matches `swiggy`, `zomato`, `restaurant`, `cafe`, `dining`, `coffee` (DEBIT only).
6. **`Transport` (`rule_id: 6`):** Matches `uber`, `ola`, `metro`, `fuel`, `petrol`, `diesel`, `auto` (DEBIT only).
7. **`Subscriptions` (`rule_id: 7`):** Matches `netflix`, `spotify`, `prime`, `youtube`, `hotstar`, `gym` (DEBIT only).
8. **Fallbacks (`rule_id: 8`):** Unmatched debits are classified as `Uncategorized`; unmatched credits as `Other Credit`.

---

## Outlier Screening Algorithm

SpendSense detects unusually large expenses within each category using the **Modified Z-Score based on Median Absolute Deviation (MAD)**:

### Algorithm Steps

1. **Eligibility Filter:** Only transactions where `transaction_type == 'DEBIT'` and `category != 'Transfer'` are screened.
2. **Independent Baselines:** Each category is evaluated independently against its own distribution. Amounts from different categories are never pooled.
3. **Calculate Category Median ($\text{median}_x$):**
   $$\text{median}_x = \text{median}(x)$$
4. **Calculate Raw MAD:**
   $$\text{MAD} = \text{median}(|x_i - \text{median}_x|)$$
5. **Guardrail 1 — Sample Size ($N \ge 5$):** A category must contain at least 5 eligible observations (including candidate). If $N < 5$, the category status is `NOT_EVALUATED_INSUFFICIENT_DATA`.
6. **Guardrail 2 — Zero MAD ($\text{MAD} == 0$):** If all amounts or median deviations are identical, raw MAD is 0. To prevent division by zero, the category status is `NOT_EVALUATED_ZERO_MAD`.
7. **Calculate Modified Z-score:**
   $$\text{ModifiedZ} = 0.6745 \times \frac{\text{candidate\_amount} - \text{median}_x}{\text{MAD}}$$
   *The scaling factor `0.6745` is applied exactly once to the raw MAD quotient.*
8. **Strict Flagging Threshold:** A transaction is flagged as a potential outlier if and only if:
   $$|\text{ModifiedZ}| > 3.5$$
   *(A score exactly equal to 3.5 is not flagged).*

### Cautious Terminology
Flagged transactions are described strictly as **potential outliers** or **potentially unusual expenses**. SpendSense never describes statistical anomalies as confirmed fraud.

---

## Running the Automated Test Suite

SpendSense includes an extensive automated test suite covering CSV validation, deterministic categorization, SQLite transactional replacement, SQL summaries, outlier mathematics, bundled examples, and HTTP server APIs.

Run the full test suite from the project root:

```powershell
python -m pytest -q
```
*Current suite status: **138 passed**.*

### Running Focused Test Suites

```powershell
python -m pytest -q tests/test_data_processing.py  # Milestone 1: CSV schema & money validation
python -m pytest -q tests/test_categorization.py   # Milestone 2: Deterministic rule categorization
python -m pytest -q tests/test_storage.py          # Milestone 3: SQLite schema & atomic replacement
python -m pytest -q tests/test_analysis.py         # Milestone 4: SQL summaries & outlier screening
python -m pytest -q tests/test_main.py             # Milestone 5: End-to-end CLI integration
python -m pytest -q tests/test_server.py           # Web UI: Local server routes, APIs, allowlist security
python -m pytest -q tests/test_examples.py         # Examples: Regression tests for all 5 bundled CSVs
```

---

## CLI Demonstration Walkthrough

You can also run SpendSense via the command line on any input CSV:

```powershell
python main.py data/sample_transactions.csv --db spendsense.db
```

### Inspecting the Terminal Output
- **Import Summary:** 16 accepted records, 0 rejected rows.
- **Ordinary Expenses:** ₹10,739.50 across Dining, Groceries, Subscriptions, and Transport.
- **Credits:** ₹85,500.00 (Income ₹75,000.00, Transfer ₹10,000.00, Refund ₹450.00, Other Credit ₹50.00).
- **Transfers:** ₹25,000.00 reported separately (DEBIT ₹15,000.00, CREDIT ₹10,000.00).
- **Potential Outlier:** `[ID 5] 2026-10-05 | Dining | Swiggy Feast` flagged with amount ₹4,200.00 and score `52.61`.
- **Not Evaluated Categories:** Groceries, Subscriptions, and Transport marked `NOT_EVALUATED_INSUFFICIENT_DATA`.

---

## Scope & Boundaries

SpendSense is designed as a focused, robust, portfolio-quality engineering implementation. By specification, it does not include:
- Bank or aggregator APIs (e.g. Plaid, Open Banking).
- Live financial institution access or real credential handling.
- Machine learning or neural models.
- Cloud database hosting or third-party analytics telemetry.
- Multi-currency conversions (all amounts are INR).
