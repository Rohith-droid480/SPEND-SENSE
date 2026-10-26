# SpendSense — Code Architecture

**Purpose:** Define the simplest clear source-code structure for the locked SpendSense MVP. This file describes how code should be divided and how data moves between modules; the locked v1.2 architecture remains the authority for exact business rules.

**Design target:** Beginner-readable, deterministic, testable Python. Use a few focused modules and functions—not classes, services, frameworks, or extra layers without a concrete requirement.

## 1. Architectural decisions

- Application type: local Python command-line application.
- Python: 3.10+.
- Application dependencies: Python standard library only.
- Test dependency: `pytest`.
- Input: one documented synthetic CSV with `Date`, `Description`, `Amount`, and `Type`.
- Persistent storage: one local SQLite `transactions` table.
- Money representation: integer paise after validation with `Decimal`.
- Categorization: ordered, explainable substring rules.
- Summary calculations: SQL `SUM`, `COUNT`, and `GROUP BY`.
- Potential-outlier calculations: standard-library median and raw MAD, independently per eligible category.

Do not add Pandas, a web framework, ORM, application class hierarchy, machine learning, APIs, scheduling, dashboards, cloud storage, or other excluded features to this MVP.

## 2. Folder and file structure

Use the structure already established by the project. The expected simple structure is:

```text
spendsense/
├── main.py                    # CLI entry point and pipeline orchestration
├── data_processing.py         # CSV structure, row validation, dates, money conversion
├── categorization.py          # Description normalization and ordered category rules
├── storage.py                 # SQLite schema, atomic replacement, reads and connection helpers
├── analysis.py                # SQL summaries and Modified Z-score screening
├── data/
│   └── sample_transactions.csv # Synthetic demo input only
├── tests/
│   └── test_spendsense.py      # Unit, edge-case, database, and end-to-end tests
├── requirements.txt            # pytest only for development/testing
├── .gitignore                  # Python caches, virtual environment, local DB/output
└── README.md                   # Goal, input contract, setup, command, tests, limitations
```

Do not move files just to match this tree if an approved, already-working layout exists. Inspect the real repository first. If the existing layout differs, report the difference and prefer minimal changes.

## 3. One-way module responsibilities

```text
                         main.py
             (coordinates; owns no business logic)
                 /          |           \
                v           v            v
     data_processing.py  categorization.py  storage.py
              |                |              ^
              |                |              |
              +------ records +---------------+
                                               
                 main.py calls analysis.py
                          |
                          v
                 analysis.py + SQLite
              (SQL summaries + MAD screening)
```

Use these dependency rules to avoid circular imports:

- `main.py` may import and call all four modules. It sequences the pipeline; it should not duplicate their logic.
- `data_processing.py` uses standard-library CSV/date/decimal tools. It does not import `main.py`, `storage.py`, or `analysis.py`.
- `categorization.py` contains normalization and rules. It does not import the database or CLI.
- `storage.py` owns database creation and safe replacement. It does not import `main.py`, `categorization.py`, or `analysis.py`.
- `analysis.py` owns summary and outlier calculations. It may use `sqlite3` directly or a small public connection helper from `storage.py`; `storage.py` must never import `analysis.py`.
- `tests/test_spendsense.py` imports the public functions it tests. Tests should not depend on executing the application as a side effect of import.

Keep logic in its owning module. Avoid a generic `utils.py` unless a real shared function cannot sensibly belong in an existing module.

## 4. End-to-end data flow

1. The user runs the CLI with the sample or another supported CSV path.
2. `main.py` calls `load_and_validate_csv(path)`.
3. `data_processing.py` returns accepted normalized records and a list of row-level rejections. It does not modify the database.
4. If the accepted-record list is empty, `main.py` reports the problem and stops before replacing database rows.
5. For each accepted record, `main.py` uses `categorization.py` to calculate `normalized_description`, `category`, and `rule_id`, preserving the original description.
6. `storage.py` initializes the schema as needed and replaces all transaction rows inside one database transaction. A successful non-empty import replaces the old dataset; a failure rolls back and preserves old rows.
7. `analysis.py` queries SQLite for expense/category totals and eligible transactions for outlier screening.
8. `main.py` prints the report and returns an appropriate process exit status.

```text
CSV file
   |
   v
load_and_validate_csv
   |-------------------------------> rejected rows + reasons
   v
accepted validated records
   |
   v
normalize + categorize each record
   |
   v
transactional SQLite replacement
   |
   +--------------------------+
   |                          |
   v                          v
SQL expense/category       category-specific
and credit summaries       median/MAD screening
   |                          |
   +------------+-------------+
                v
         terminal report
```

There is no background processing, web service, event bus, or multi-user layer.

## 5. Canonical record shapes

Use ordinary dictionaries with consistent keys for this small MVP. Do not introduce a custom model class solely to hold these values.

### Accepted record before categorization

`data_processing.py` returns a record with:

```python
{
    "transaction_date": "2026-10-03",  # valid ISO date string
    "description": "DMART STORE 018",  # original text, preserved
    "transaction_type": "DEBIT",      # only DEBIT or CREDIT
    "amount_paise": 12550,             # positive int, never float
}
```

The dates and values shown are examples only.

### Record passed to SQLite

After the categorization step, the record contains all persisted fields except database-generated `id`:

```python
{
    "transaction_date": "2026-10-03",
    "description": "DMART STORE 018",
    "normalized_description": "dmart store 018",
    "transaction_type": "DEBIT",
    "amount_paise": 12550,
    "category": "Groceries",
    "rule_id": "R_GROCERIES",
}
```

The names, types, and semantics must be consistent across modules. Do not store the amount as `float`, store rupee decimals in the database, or overwrite the original description with its normalized form.

### Rejected row

Store enough information to explain a rejection, such as:

```python
{
    "record_number": 4,
    "reason": "amount has more than two decimal places",
}
```

Use a stable record-number convention and explain physical-line versus logical-record numbering for multiline CSV fields. Do not needlessly echo full transaction content in error reports.

## 6. File-by-file design and function contracts

### `main.py` — pipeline and CLI only

Responsibilities:

- Parse the CSV path using a simple documented command.
- Set the local database path in one obvious place or through a small CLI argument.
- Call the processing, categorization, storage, and analysis functions in the correct order.
- Stop before database replacement when no accepted rows exist.
- Print the results in understandable sections.
- Return a non-zero exit status for file/schema-level failures or unsuccessful import; do not swallow failures and print success.

Keep validation, SQL statements, category patterns, and statistical math out of `main.py`.

Suggested public entry point:

```python
def main() -> int:
    """Run the CLI pipeline and return a process exit code."""
```

If tests need to call the workflow without simulating CLI arguments, a small `run_pipeline(csv_path, db_path)` function may be used. Add it only if it genuinely improves testability; do not create a large command framework.

### `data_processing.py` — input boundary

Responsibilities:

- Open CSV files safely with a documented encoding and newline handling.
- Validate the header: required columns, duplicates, unsupported/missing columns, and collision with the reserved `restkey`.
- Read with `csv.DictReader` and explicitly detect extra fields and missing fields.
- Validate `Date`, `Description`, `Amount`, and `Type`.
- Convert `Amount` directly from text through `Decimal` to positive integer paise.
- Return row-level rejection reasons while continuing on independent bad rows when CSV structure remains parseable.
- Treat `csv.Error`, an unreadable file, empty file, or invalid header as a clear file-level failure.
- Never write to SQLite.

Suggested public functions:

```python
def to_paise(amount_text: str) -> int:
    """Validate positive money text and return exact integer paise."""


def load_and_validate_csv(path):
    """Return (accepted_records, rejected_records) for a valid CSV schema."""
```

`to_paise` should raise a clear `ValueError` (or one consistent, documented validation exception) for invalid amount text. `load_and_validate_csv` should convert row-specific validation errors into rejection records. For file-level failures, use one clear exception/return convention consistently; do not use an ambiguous mix of silent `None`, empty lists, and printed messages.

Money requirements:

- Reject invalid, non-finite, zero, negative, and values not exactly representable to two decimal places.
- `10.50` becomes `1050` paise.
- `12.345` is rejected, not rounded.
- `12.340` may be accepted and normalized to `12.34`.
- Do not parse through binary `float` first.

Structural validation requirements:

- Set a dedicated `restkey`, such as `__EXTRA_COLUMNS__`.
- Reject a record with extra values under the reserved key.
- Reject a record when a required field value is `None` because fields are missing.
- Reject a header containing the reserved `restkey` name.
- `DictReader` can raise `csv.Error`; report it as a file-level parsing failure.
- Test a valid row immediately before and after malformed rows.

### `categorization.py` — deterministic, explainable rules

Responsibilities:

- Normalize description text by trimming and lowercasing for matching.
- Preserve the original description elsewhere in the record.
- Apply explicit, deterministic rule order.
- Respect each rule's transaction-type scope (`DEBIT`, `CREDIT`, or `ANY`).
- Return both the selected category and `rule_id`.
- Provide fallback categories if no rule matches.

Suggested public functions:

```python
def normalize_description(description: str) -> str:
    """Return the normalized matching text."""


def categorize_transaction(description: str, transaction_type: str) -> tuple[str, str]:
    """Return (category, rule_id) for the first applicable rule."""
```

Keep the rule list near the categorization function and order specific patterns before broader patterns (for example, `uber eats` before `uber`). Use the rules in the locked architecture; do not make unrequested changes to categories or semantics.

Required fallbacks:

- unmatched `DEBIT` → `Uncategorized`;
- unmatched `CREDIT` → `Other Credit`.

Store the selected `rule_id` so the category decision can be explained later.

### `storage.py` — one SQLite table and safe replacement

Responsibilities:

- Create the exact `transactions` table and constraints from the locked architecture.
- Use SQLite through `sqlite3` and parameterized statements with `?` placeholders.
- Replace the currently imported dataset atomically.
- Retrieve records needed by analysis/reporting.
- Close connections reliably, preferably with context managers.

Required table:

```sql
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
```

Suggested public functions:

```python
def initialize_database(db_path) -> None:
    """Create the table if it does not exist."""


def replace_transactions(db_path, records) -> int:
    """Atomically replace existing transaction rows and return inserted count."""


def read_transactions(db_path) -> list[dict]:
    """Return the current stored transactions needed for output/tests."""
```

Replacement rules:

1. Validate the CSV completely before calling replacement.
2. Do not call replacement with an empty accepted list.
3. Ensure the table exists.
4. Delete and insert within a single transaction.
5. Insert values using `?` placeholders and `executemany`.
6. Commit only after all inserts succeed; roll back on any failure.
7. Do not deduplicate identical rows in one input file.
8. A successful re-import replaces the previous dataset rather than appending.

A test must deliberately trigger an insertion failure and confirm previous rows remain. Do not claim rollback was tested unless that test ran.

### `analysis.py` — SQL totals and statistical screening

Responsibilities:

- Calculate totals from the accepted SQLite dataset.
- Use SQL `SUM`, `COUNT`, and `GROUP BY` for expense/category/credit summaries.
- Apply documented filters so credits and transfers do not inflate ordinary expense totals.
- Retrieve eligible transaction amounts for the statistical screen.
- Calculate raw MAD and Modified Z-score using `statistics.median`.
- Return data/status values; do not own the CLI's entire printed report.

Suggested public functions:

```python
def calculate_summary(db_path) -> dict:
    """Return expense, category, credit, and transfer summaries from SQL."""


def detect_potential_outliers(db_path) -> dict:
    """Return flagged potential outliers and explicit not-evaluated statuses."""
```

Summary semantics:

- Expenses: `DEBIT` and category is not `Transfer`.
- Expense by category: the same filter, grouped by category.
- Credits: separate from expenses and grouped by inferred category.
- Transfers: separate; exclude them from expenses and outlier baselines.
- Refunds remain separate credit records; do not net them against purchases.

Outlier rules:

```text
median_x = median(x)
absolute_deviations = [abs(value - median_x) for value in x]
MAD = median(absolute_deviations)
ModifiedZ(value) = 0.6745 * (value - median_x) / MAD
```

- Eligible values are `DEBIT` records that are not transfers.
- Compute one baseline per category.
- Require at least five eligible observations, including the candidate.
- If too few observations: `NOT_EVALUATED_INSUFFICIENT_DATA`.
- If raw MAD equals zero: `NOT_EVALUATED_ZERO_MAD`.
- Otherwise flag only when `abs(score) > 3.5`.
- Use raw MAD and apply `0.6745` exactly once.
- Never divide by zero or describe an un-evaluated group as anomaly-free.
- Report “potential outlier,” not fraud.

### `tests/test_spendsense.py` — prove behavior

Use `pytest`, synthetic input, and temporary files/database paths. Test public function behavior, not private implementation details unless needed for a critical failure path.

Keep tests readable. Name each test after the expected behavior. Do not use real personal financial data. Make edge cases easy to understand from the fixtures.

## 7. CLI behavior

Keep the command obvious and document it in `README.md`. Preferred basic run:

```bash
python main.py data/sample_transactions.csv
```

If the repository layout needs a different working directory or command, choose one consistent command and document that exact command. Do not create several alternative entry points.

The report should include:

1. input path and import outcome;
2. records read, accepted, and rejected;
3. rejection record numbers and concise reasons;
4. total expenses, excluding transfers;
5. expense totals by category;
6. credits/refunds and transfers as separate summaries;
7. flagged potential outliers and their scores;
8. not-evaluated outlier groups and reasons;
9. database path and the fact that a successful import replaces the prior dataset.

Format integer paise as INR for display, e.g. `₹1,234.50`. Do not infer that a category label proves the user's actual intent. Do not print sensitive full row contents unnecessarily.

## 8. Error-handling policy

Handle expected input problems with clear messages and stable behavior. Avoid broad `except Exception` blocks that hide programming bugs.

- Row validation problem → reject that row with record number and reason; continue when safe.
- Missing/unreadable/empty file, invalid header, or malformed CSV parser error → report import failure; do not replace the database.
- Zero accepted rows → report failure/no import; preserve current stored rows.
- Database replacement failure → roll back; report failure; preserve old rows.
- Statistical group too small or MAD zero → return an explicit not-evaluated status, not an exception or a false “no outliers” statement.
- Unexpected programming/database exceptions → surface a clear failure at the application boundary, preserve rollback behavior, and never print success when the operation failed.

Do not catch and discard errors merely to keep the program running.

## 9. Test architecture and required cases

### Input / money

- valid row and valid CSV;
- missing file, empty file, invalid/missing/duplicate/unsupported headers;
- reserved `restkey` collision;
- extra-field row and missing-field row;
- valid rows immediately before and after bad rows;
- invalid date, blank description, invalid type;
- `10.50`, `12.340`, `12.345`, zero, negative, NaN, infinity;
- file-level `csv.Error` behavior if reproducible with the chosen parser/input.

### Categorization

- trimming and lowercasing;
- overlapping rules and priority order;
- transaction-type scope;
- retained original description;
- `rule_id` correctness;
- unknown debit and credit fallback categories.

### Database and summaries

- schema and constraints;
- parameterized insert path;
- initial import and successful replacement;
- repeated import does not append a second copy of the old batch;
- identical rows within one CSV are both retained;
- zero-accepted import preserves existing rows;
- simulated insert failure rolls back;
- totals match a hand-calculated dataset;
- credits, refunds, and transfers are treated separately.

### Outliers and full pipeline

- one extreme value in a category with enough data and nonzero MAD;
- insufficient category data;
- zero-MAD category;
- exclusion of credits and transfers;
- exact threshold behavior around `abs(score) > 3.5` where practical;
- complete command produces a report that matches the sample database and data.

## 10. Beginner-readability standards

- One module should have one obvious responsibility.
- Functions should fit on a screen where practical and do one job.
- Prefer names like `amount_paise`, `accepted_records`, `rejected_records`, and `normalized_description` over abbreviations.
- Use explicit `if` statements when they are easier to understand than dense expressions.
- Comments should explain non-obvious business/statistical behavior, not restate the code.
- Do not add classes, dataclasses, decorators, generic repository patterns, a service layer, dependency injection, or plugin frameworks unless there is an approved reason.
- Avoid making a single function handle CSV reading, database writes, summaries, and printing.
- Explain the key path in terms of inputs, transformations, stored fields, SQL queries, and report outputs.

## 11. Definition of code-architecture completion

This architecture is implemented when:

- source files follow the responsibilities above, or an already-approved equivalent is documented;
- imports flow in one direction without circular imports;
- the pipeline passes records through the documented shape;
- database writes are isolated in `storage.py`;
- SQL summaries and MAD logic are in `analysis.py`, not hidden in `main.py`;
- tests cover critical success and failure paths;
- the README command works against the synthetic sample;
- no optional feature or dependency has been added without approval.

**Authority reminder:** This file organizes the code; it does not change the locked v1.2 requirements. If a discrepancy appears, follow the locked architecture and flag the issue rather than silently changing behavior.
