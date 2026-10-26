# SpendSense — Final MVP Architecture (Revised after Gemini Validation)

**Version:** 1.2  
**Status:** FINAL LOCKED MVP ARCHITECTURE — ready for implementation after applying the explicit CSV structural-validation rule below  
**Deadline:** Wednesday; approximately 2.5 days of focused work  
**Application type:** Local Python command-line application  
**Currency for the demo:** INR, stored in integer paise

## 1. Final project goal

SpendSense imports one documented CSV of synthetic transactions, validates each record with a clear row-level rejection reason, categorizes transactions with explainable rules, saves accepted records to SQLite, calculates spending totals using SQL, screens eligible expense transactions for potential outliers using a category-specific Modified Z-score, and prints a readable report.

The project demonstrates a complete data workflow: input validation, business rules, SQL persistence and aggregation, robust descriptive statistics, error handling, and tests. It is an educational expense-analysis tool, not a bank integration, fraud detector, or production financial system.

### Definition of done

The MVP is done when:

1. One documented command runs the whole pipeline locally.
2. It accepts a CSV following the fixed input contract below.
3. Invalid rows are reported with a CSV record number and a concise rejection reason.
4. Valid records are categorized deterministically; unmatched records remain explicitly uncategorized.
5. Money is parsed with `Decimal` and stored as integer paise.
6. Accepted records can be written to and read from SQLite.
7. Expense totals and category totals match hand-checked examples.
8. The Modified Z-score logic safely handles insufficient sample sizes and zero MAD.
9. The terminal report distinguishes potential outliers from fraud.
10. The tests pass locally, and the README explains installation, input format, execution, tests, and limitations.

The deadline is a planning constraint, not a guarantee. Do not add optional features until this checklist passes.

## 2. Scope decisions

### Included in the Wednesday MVP

- One fixed, synthetic CSV format.
- Row-by-row validation with `csv.DictReader`.
- Decimal-based amount parsing and integer-paise storage.
- Simple description normalization and prioritized substring rules.
- One SQLite `transactions` table.
- Transactional replacement of the accepted dataset on a successful import.
- SQL `GROUP BY` summaries.
- Category-specific Modified Z-score outlier screening using Python's standard library.
- Terminal report, tests, synthetic data, README, and `.gitignore`.

### Explicitly excluded

- Pandas in the initial implementation. See Section 3 for the trade-off.
- Recurring-payment detection.
- Plaid or other financial APIs, banking credentials, and real account access.
- Machine-learning classifiers, PSI/data drift, or claims of fraud detection.
- Streamlit or another dashboard.
- Telegram/email notifications, scheduled jobs, GitHub Actions, cloud databases, or deployment.
- Multi-currency support and universal bank-statement parsing.
- Multiple users, concurrent writers, WAL tuning, ORM frameworks, and elaborate configuration layers.

## 3. Technology choices

| Technology | Decision | Responsibility | Reason |
|---|---|---|---|
| Python 3.10+ | Required | Orchestration, data rules, reporting, statistics | Readable code; needed modules are in the standard library |
| `csv.DictReader` | Required | Read CSV records and identify row-level validation failures | Gives direct access to each record and its source row/line information without a DataFrame conversion |
| `decimal.Decimal` | Required | Parse monetary text exactly before conversion | Avoids deriving paise from binary floating-point values |
| `sqlite3` | Required | Persist records and run summary queries | Built-in local relational database, no server required |
| `statistics.median` | Required | Calculate median and raw MAD | Enough for the selected Modified Z-score; avoids a statistics package |
| `pytest` | Required for tests | Verify functions and integration behavior | Concise tests using normal `assert` statements; one development dependency |

### Pandas trade-off

Gemini's validation identified a mismatch between mandatory Pandas ingestion and the requirement for beginner-friendly, per-record rejection reasons. SpendSense therefore uses `csv.DictReader` for ingestion and validation and SQLite `GROUP BY` for expense aggregation. Pandas is not needed for the selected MVP. This is a deliberate scope decision, not a claim that iterating over a small CSV is inherently bad practice. Pandas can be introduced later if the project grows into broader exploratory analysis or more complicated transformations.

## 4. High-level data flow

```text
User runs main.py with a CSV path
                 |
                 v
        Read CSV with DictReader
                 |
                 v
      Validate each row and record
       accepted rows / rejected rows
                 |
                 v
       Normalize description text
       and apply ordered category rules
                 |
                 v
       Convert Amount text to paise
                 |
                 v
   If no valid rows: report and do not replace DB
                 |
                 v
   Atomic SQLite replacement transaction
                 |
                 v
       Read accepted rows from SQLite
                 |
          +------+------+
          |             |
          v             v
 SQL GROUP BY sums   Python median/MAD
 category totals     per eligible category
          |             |
          +------+------+
                 v
        Print terminal report
```

This is one sequential script with small modules, not a microservice or distributed architecture.

## 5. Input CSV contract

The application accepts a single schema. The header row must contain exactly these four required columns, with optional surrounding whitespace removed from header names. Duplicate, missing, or ambiguous required headers are rejected. Extra columns are not part of the supported MVP contract and should produce a clear schema error rather than be silently interpreted.

| Column | Example | Required rule |
|---|---|---|
| `Date` | `2026-10-03` | Required; exact `YYYY-MM-DD` format and valid calendar date |
| `Description` | `DMART STORE 018` | Required; not empty or only whitespace |
| `Amount` | `125.50` | Required; positive decimal INR amount with at most two meaningful fractional digits; no currency symbol or thousands separator |
| `Type` | `DEBIT` or `CREDIT` | Required; trim and normalize case, then accept only these two values |

This is SpendSense's input format, not a universal bank-export format. `Amount` is always entered as a positive value; `Type` determines its meaning. A `DEBIT` is an outgoing transaction and a `CREDIT` is incoming. This contract assumes one currency (INR) for the demo.

### Amount conversion

1. Read the amount as text.
2. Parse it with `Decimal`.
3. Reject non-finite values, values less than or equal to zero, and values not exactly representable to two decimal places.
4. Multiply the validated decimal amount by 100 and convert to an integer paise value.
5. Store and aggregate the integer. Format as rupees only for display.

Do not parse into `float` first. For example, `125.50` becomes `12550` paise. A value such as `12.345` must be rejected rather than rounded silently. A value written as `12.340` is numerically exactly representable to two decimal places, so it may be accepted and normalized to `12.34` if the implementation explicitly follows numeric equivalence.

### Row-level validation and rejection reporting

Use `csv.DictReader` to process one data record at a time. **Explicitly detect structural row errors:** configure a dedicated `restkey` such as `__EXTRA_COLUMNS__` and inspect every parsed dictionary for that key; if it is present with extra values, reject the record as having extra columns. Also inspect every required field for a `None` value, which indicates that the record supplied too few fields for the header, and reject it as having missing columns. Do not assume `DictReader` raises an exception for these cases: by default, extra fields are stored under a `None` key and missing fields receive a `None` value. Reject a header that itself contains the reserved `restkey` name. You may also use `restval=None` explicitly to make the missing-field behavior clear.

The header is row 1; ordinary single-line records are numbered starting at row 2. If physical line tracking is needed for a quoted multiline record, use the reader's `line_num` and explain the distinction between physical line number and logical CSV record number. A malformed CSV quoting structure may raise `csv.Error`; catch it and report a file-level parsing error rather than pretending it is an ordinary field-validation failure.

Check each structurally valid record for required values, date validity, amount validity, and accepted `Type`. Store rejected records in memory with the row/record number and a concise reason such as `invalid date`, `amount must be positive`, `amount has more than two decimal places`, `empty description`, or `Type must be DEBIT or CREDIT`. Do not silently drop rows and do not include full sensitive values in logs.

A missing file, empty file, invalid header, or zero valid records must produce a clear unsuccessful result. Critically, do not delete or replace the prior database when the input file is missing, empty, or contains no accepted records.

## 6. Categorization and transaction semantics

Normalize descriptions for matching by trimming surrounding whitespace and converting to lowercase. Preserve the original description for reporting. Avoid aggressive punctuation or digit removal, which can merge distinct merchants.

Use a simple ordered list of rules. Each rule contains `rule_id`, substring pattern, category, applicable transaction type (`DEBIT`, `CREDIT`, or `ANY`), and priority. More specific patterns must be tested before broader patterns; the first applicable match wins. If no rule matches, use `Uncategorized` for debits and `Other Credit` for credits.

Illustrative rules (not universal merchant classifications):

| Priority | Rule ID | Pattern | Applies to | Category |
|---:|---|---|---|---|
| 1 | `R_TRANSFER` | `internal xfer`, `transfer`, `xfer` | ANY | `Transfer` |
| 2 | `R_REFUND` | `refund`, `reversal` | CREDIT | `Refund` |
| 3 | `R_INCOME` | `salary`, `payroll`, `paycheck` | CREDIT | `Income` |
| 10 | `R_DINING` | `uber eats`, `swiggy`, `zomato` | DEBIT | `Dining` |
| 20 | `R_GROCERIES` | `dmart`, `bigbasket`, `wholefoods` | DEBIT | `Groceries` |
| 30 | `R_SUBSCRIPTION` | `netflix`, `spotify`, `prime video` | DEBIT | `Subscriptions` |
| 40 | `R_TRANSPORT` | `uber`, `ola`, `shell`, `fuel` | DEBIT | `Transport` |
| 90 | `R_UNKNOWN_DEBIT` | fallback | DEBIT | `Uncategorized` |
| 91 | `R_UNKNOWN_CREDIT` | fallback | CREDIT | `Other Credit` |

The rule examples are synthetic and must be tested. A description-based label is an inference, not proof of the transaction's true purpose. Save both the normalized description and `rule_id` so the chosen category can be explained.

### Summary semantics

- **Total expenses:** sum integer-paise values for `DEBIT` records except transactions categorized as `Transfer`.
- **Expenses by category:** apply the same filter, then group by category.
- **Credits:** report incoming credits separately, grouped by inferred labels such as `Income`, `Refund`, `Other Credit`, and `Transfer`.
- **Transfers:** report separately; exclude identified transfers from ordinary expense totals and anomaly baselines whether the transfer is debit or credit.
- **Refunds:** show identifiable refunds as credits in their own category. Do not automatically treat every credit as income, and do not net refunds against the original expense because matching/reconciliation is out of scope.

## 7. SQLite storage and repeated runs

Use one table for the accepted transaction records. Derived totals and anomaly scores are calculated when the report is generated, not persisted as a second source of truth.

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

Use validated ISO-format date strings and integer paise. Do not create uniqueness from date + description + amount: two legitimate purchases may have identical values. An auto-incrementing local `id` is sufficient because the MVP does not claim to maintain cross-import transaction identity.

### Atomic replacement policy

The database represents the latest successfully accepted CSV import, not a running history of all imports.

1. Read and validate the file before changing the existing data.
2. If there are no accepted records, report the issue and preserve the existing database contents.
3. Ensure the table exists.
4. Begin a database transaction.
5. Delete the old rows and insert the new accepted rows using parameterized SQL (`?` placeholders) and `executemany`.
6. Commit only if all inserts succeed. If any operation fails, roll back, preserve the old data, report a clear error, and close the connection.

Do not deduplicate identical-looking records inside the current CSV. The replacement policy means rerunning a valid file replaces the previous batch instead of appending it a second time. Tell the user this behavior in the terminal report and README.

Use ordinary SQLite behavior; no WAL, explicit concurrency tuning, or ORM is needed for this single-user CLI application.

### SQL summaries

Use SQLite `SUM`, `COUNT`, and `GROUP BY` to calculate total expenses and category totals. For example:

```sql
SELECT category, SUM(amount_paise) AS total_paise, COUNT(*) AS transaction_count
FROM transactions
WHERE transaction_type = 'DEBIT' AND category <> 'Transfer'
GROUP BY category
ORDER BY total_paise DESC;
```

Run an additional query for overall expense total, and a separate query for credits/transfers using the documented semantics. Format integer paise as INR in Python for display. Do not aggregate expense, income, refunds, and transfers into one ambiguous total.

## 8. Potential-outlier detection

Use a category-specific Modified Z-score based on **raw** Median Absolute Deviation. Fetch eligible debit expense amounts from SQLite and calculate scores in Python with the standard library `statistics.median`.

For a category with amounts `x`:

```text
median_x = median(x)
absolute_deviations = [abs(value - median_x) for value in x]
MAD = median(absolute_deviations)
ModifiedZ(value) = 0.6745 * (value - median_x) / MAD
```

Flag a potential outlier when `abs(ModifiedZ(value)) > 3.5`. Apply the `0.6745` factor exactly once; do not use a MAD that has already been normal-scaled. Because the formula uses a ratio, calculating on integer paise or the corresponding rupee values gives the same score, barring implementation issues.

### Eligibility and safety behavior

- Use only `DEBIT` transactions that are not categorized as `Transfer`.
- Calculate a separate baseline within each category; do not mix rent-like purchases and small subscription purchases into one group.
- Require at least five eligible transactions in that category, including the candidate. This is a project guardrail, not a universal statistical guarantee.
- If the category has too few transactions, return `NOT_EVALUATED_INSUFFICIENT_DATA`.
- If raw MAD is zero, return `NOT_EVALUATED_ZERO_MAD`; do not divide by zero and do not claim no anomalies exist.
- Otherwise calculate scores consistently and flag values exceeding the chosen threshold.
- For each flagged transaction, show date, description, amount, category, score, and a short explanation.
- Use the words **potential outlier** or **potentially unusual expense**. Never call it fraud or claim statistical significance from the threshold alone.

The synthetic sample should contain at least six debit expenses in a single category, including one deliberately extreme amount, so both the scoring and flagged-output paths can be demonstrated. Also include a repeated-value category to test zero MAD. The output must clearly disclose that this is a simple educational screening rule, not a validated financial risk model.

Primary statistical reference: NIST Engineering Statistics Handbook, “Detection of Outliers”: https://www.itl.nist.gov/div898/handbook/eda/section3/eda35h.htm

## 9. Simple module structure

```text
spendsense/
├── main.py                     # Entry point and pipeline orchestration
├── data_processing.py          # CSV reading, row validation, dates and Decimal-to-paise conversion
├── categorization.py           # Description normalization and ordered rules
├── storage.py                  # Schema creation, atomic replacement, read/query helpers
├── analysis.py                 # SQL-based summaries and Python Modified Z-scores
├── data/
│   └── sample_transactions.csv # Synthetic demo input
├── tests/
│   └── test_spendsense.py      # Unit and database tests
├── requirements.txt            # pytest only
├── .gitignore                  # venv, caches, database and local outputs
└── README.md                   # Goal, input contract, setup, run, tests and limits
```

No class hierarchy is needed. Keep functions small enough that a beginner can trace inputs and outputs.

| Function | Responsibility | Expected result |
|---|---|---|
| `load_and_validate_csv(path)` | Check headers; process each CSV record; validate date, description, amount and type | Accepted records and rejected-record details |
| `to_paise(amount_text)` | Parse with `Decimal`, validate precision/range and convert to paise | Positive integer paise or a clear validation error |
| `categorize_transaction(description, transaction_type)` | Apply normalized ordered rules | `(category, rule_id)` |
| `initialize_database(db_path)` | Create the transactions table if needed | Initialized local database |
| `replace_transactions(db_path, records)` | Atomically replace rows with validated records | Number of inserted records |
| `read_transactions(db_path)` | Retrieve the currently accepted records | Records for reporting and anomaly analysis |
| `calculate_summary(db_path)` | Run SQL sums and `GROUP BY` queries | Expense/category/credit/transfer summary |
| `detect_potential_outliers(db_path)` | Apply category-specific raw-MAD Modified Z-scores | Flagged and not-evaluated results with reasons |
| `main()` | Orchestrate input, processing, storage, analysis, and report | Clear terminal result and exit status |

## 10. Terminal report

Print:

1. Input file and import outcome.
2. Number of data records read, accepted, and rejected.
3. Rejected record numbers and concise reasons.
4. Total expenses in INR, excluding identified transfers.
5. Expense totals by category.
6. Credit totals, with inferred Income, Refund, Other Credit, and Transfer labels where rules support them.
7. Potential outliers with category and Modified Z-score.
8. Categories not evaluated due to insufficient data or zero MAD.
9. Database location and confirmation that a successful import replaces the prior dataset.
10. Runtime only if measured; identify it as a local measurement, not a general benchmark.

Format monetary values as `₹1,234.50` from integer paise. Avoid printing full potentially sensitive transaction contents for rejected rows.

## 11. Testing and acceptance criteria

Use pytest with synthetic fixtures and temporary database paths. These tests are proposed requirements; mark them as passing only after running them.

| Test | Expected behavior |
|---|---|
| Valid CSV | Expected records accepted and categorized |
| Missing file, empty file, missing/duplicate header | Clear error; existing DB unchanged |
| Invalid date, amount, description, or type | Rejected row includes row/record number and reason; other valid rows proceed |
| Amount `10.50` | Converts to 1050 paise |
| Amount `12.345`, zero, negative, NaN or infinity | Rejected without silently rounding or accepting |
| Categorization overlap | Highest-priority applicable specific rule wins |
| Unknown debit/credit | Uses documented fallback category |
| Expense summary | Matches hand-calculated category totals; credits excluded |
| Refund and transfer | Refund is separate credit; transfers excluded from expense summary and anomaly baseline |
| Potential outlier | A deliberately extreme value is flagged when the category is eligible and MAD is nonzero |
| Insufficient category history | Reports `NOT_EVALUATED_INSUFFICIENT_DATA` |
| Zero-MAD group | Reports `NOT_EVALUATED_ZERO_MAD` without a crash |
| Identical rows within one CSV | Both rows are preserved |
| Successful re-import | New accepted dataset replaces previous rows; no append duplication |
| All rows invalid | Existing dataset remains unchanged |
| Insert failure during replacement | Transaction rolls back; prior accepted records remain intact |
| End-to-end synthetic run | Console report matches the sample data and database contents |

## 12. Implementation order for 2.5 days

### Phase 1 — CSV contract and row validation
- Create the repository, sample CSV, and virtual environment.
- Implement `csv.DictReader`, header validation, row numbering, date checks, and `Decimal`-based paise conversion.
- Print accepted/rejected counts and reasons.

**Checkpoint:** input errors are clear, and money is converted without using float as the source.

### Phase 2 — Categories and SQLite
- Implement ordered rules and retain `rule_id`.
- Create the table and implement atomic replacement with bound SQL parameters.
- Query inserted records and confirm duplicate-looking rows in one file remain distinct.

**Checkpoint:** validated transactions survive a successful run and failed replacement does not corrupt the previous dataset.

### Phase 3 — Summaries, anomaly screening, tests
- Implement SQL category summaries and separate credit/transfer totals.
- Implement Modified Z-score using raw MAD and test edge cases.
- Add pytest tests throughout rather than leaving all testing to the end.

**Checkpoint:** hand-calculated totals and expected statistical cases match.

### Phase 4 — Demo and handoff
- Generate the report, test from a clean environment, write the README and `.gitignore`.
- Rehearse explaining each module, money conversion, SQL grouping, formula, and limitations.

**Checkpoint:** another person can follow the README and reproduce the demo.

If time becomes tight, prioritize a complete, tested pipeline over any additional feature. Recurrence detection, a dashboard, APIs, alerts, and scheduling remain deferred.

## 13. Privacy and honest presentation

- Use synthetic transactions in the repository.
- Do not commit personal bank statements or generated local SQLite databases.
- Do not request or store banking credentials.
- Use parameterized SQL values.
- Do not claim fraud detection, production deployment, prediction, or financial advice.
- Do not claim accuracy/performance improvements or successful tests until measured.

Suggested resume description, to be used only after these features are implemented:

> Built a local Python expense-analysis pipeline that validates transaction CSV records, categorizes descriptions using prioritized explainable rules, stores amounts as integer paise in SQLite, calculates SQL-based spending summaries, and flags potential outliers using category-specific Modified Z-scores with explicit edge-case handling.

## 14. Technical references for implementation checks

These references support specific technical behavior; they do not establish that this architecture is universally optimal. Recheck version-specific behavior when implementing.

- Python `csv`: https://docs.python.org/3/library/csv.html
- Python `decimal`: https://docs.python.org/3/library/decimal.html
- Python `sqlite3`: https://docs.python.org/3/library/sqlite3.html
- SQLite transactions: https://www.sqlite.org/lang_transaction.html
- NIST outlier detection: https://www.itl.nist.gov/div898/handbook/eda/section3/eda35h.htm
- pytest: https://docs.pytest.org/en/stable/

## 15. Final validation and architecture lock

**Final status: PASS WITH THE CSV STRUCTURAL-CHECK CLARIFICATION INCORPORATED.** The previous validation found no critical or major blockers. Its sole remaining minor issue is resolved by the explicit `restkey`/missing-field checks in Section 5. This status means the architecture is sufficiently specified to begin implementation; it does not mean the future code has been executed or that its tests have passed.

Before considering the input-validation implementation complete, test both structural cases:

- A row with one extra field is rejected with an “extra columns” reason.
- A row with one missing field is rejected with a “missing columns” reason.

Also test a valid row immediately before and after each malformed row to confirm row-level rejection does not accidentally discard adjacent valid records. If the CSV parser raises a file-level `csv.Error`, report it clearly and preserve the existing database.

Build the local CLI pipeline in the phase order above. Use `csv.DictReader` for transparent row-level validation, SQLite for persistent storage and aggregate summaries, Python's `Decimal` for amount conversion, and Python's standard-library median for the selected outlier calculation. Do not add optional features until the acceptance tests pass.
