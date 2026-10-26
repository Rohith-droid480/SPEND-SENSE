# SpendSense — Project Context & AI Handoff File

**Purpose:** Keep ChatGPT, Antigravity IDE, and any independent validator aligned on the same project goal, architecture, implementation status, and working rules.

**Project:** SpendSense — Expense Pattern & Anomaly Detector  
**Context version:** 1.0  
**Technical architecture baseline:** `SpendSense_Final_Architecture_LOCKED_v1_2.md`  
**Status at creation:** Architecture locked; implementation and tests must be verified from the actual repository. Do not assume code exists or tests pass merely because the architecture was approved.

---

## 1. Read this first

SpendSense is a small, local Python command-line application for analysing a synthetic expense CSV. It validates transaction rows, applies explainable rule-based categories, stores accepted transactions in SQLite, calculates summaries with SQL, and screens eligible expenses for potential outliers with a category-specific Modified Z-score.

The goal is to build a **complete, simple, testable, explainable MVP**, not a large financial product. The user is a beginner and needs to understand the code, not just receive code that appears to work.

### Source-of-truth order

1. **`SpendSense_Final_Architecture_LOCKED_v1_2.md`** is the detailed, locked technical specification. Follow it for exact requirements and edge cases.
2. **This `SpendSense_PROJECT_CONTEXT.md`** is the orientation, collaboration protocol, and concise reminder of non-negotiable choices.
3. Existing repository code and tests show the actual implementation state, but do not silently override the locked requirements. If code conflicts with the architecture, flag it and propose a minimal correction.
4. AI reports and suggestions are review inputs, not automatic approval to change the architecture.

If a requirement seems contradictory or impossible, explain the conflict and ask ChatGPT/the user to decide before changing a locked choice. Do not silently expand scope.

## 2. What the finished MVP must do

Given one CSV that follows the SpendSense schema, the app must:

1. Read and validate records with Python's `csv.DictReader`.
2. Reject malformed or invalid records with a record/line reference and a clear reason; continue processing other structurally valid records when safe.
3. Parse monetary text with `Decimal`, validate it, and store money as integer paise. Do not parse to `float` first.
4. Categorize transactions using ordered, explainable substring rules and retain a `rule_id` for every category decision.
5. Store accepted records in one SQLite `transactions` table.
6. Replace the previous imported dataset atomically only when a new import has accepted records and all database operations succeed.
7. Calculate expense and category totals with SQL (`SUM`, `COUNT`, `GROUP BY`); keep credits and transfers distinct from ordinary expenses.
8. Screen eligible debit expenses using a category-specific Modified Z-score calculated from the raw Median Absolute Deviation (MAD).
9. Print an understandable terminal report including import counts, rejected-row reasons, expense totals, category totals, credit/transfer summaries, potential outliers, and cases not evaluated.
10. Include synthetic sample data, tests, a README, and a `.gitignore`.

## 3. Locked decisions — do not change without approval

### Technology

- Python 3.10+.
- Standard-library `csv`, `decimal`, `sqlite3`, and `statistics.median`.
- `pytest` as the only required development/test dependency.
- SQLite database stored locally.
- INR demo amounts, converted to integer paise for storage and arithmetic.
- No Pandas in this MVP. CSV row-level rejection reasons and SQLite summaries are intentional choices.

### Explicitly out of scope

Do not add these before all acceptance tests pass:

- machine learning, fraud detection claims, or claims that the app predicts fraud;
- Pandas, dashboards, Streamlit, web apps, or mobile apps;
- bank APIs, Plaid, credentials, or actual bank-account access;
- recurring-payment detection, email/Telegram alerts, scheduling, or CI/CD;
- cloud hosting, server databases, ORM frameworks, microservices, or multi-user support;
- multi-currency support, universal bank-statement parsing, or complex configuration layers;
- advanced statistical methods beyond the defined Modified Z-score screening.

If time is tight, finish and test the smallest full pipeline rather than implementing optional features.

## 4. CSV input contract

The supported CSV has exactly these four required headers:

- `Date`: valid calendar date in `YYYY-MM-DD` format.
- `Description`: non-empty text after trimming whitespace.
- `Amount`: positive INR decimal text, exactly representable to two decimal places; no currency symbol or thousands separator.
- `Type`: `DEBIT` or `CREDIT`, case/whitespace normalized before validation.

`Amount` is always positive; `Type` defines whether money goes out or comes in. This is a project-specific synthetic-data contract, not a universal format for bank exports.

### Structural validation is mandatory

`csv.DictReader` does not automatically raise for rows with extra or missing fields. Implement explicit checks:

- Set a reserved `restkey`, e.g. `__EXTRA_COLUMNS__`, and reject a record if extra values are present under that key.
- Inspect required fields for `None`, which identifies missing values caused by too few fields.
- Reject a header that collides with the reserved `restkey`.
- Validate missing, duplicate, or unexpected headers clearly; do not silently accept an ambiguous schema.
- Handle `csv.Error` as a file-level parsing failure.
- Test a valid row before and after each malformed row.

The header is record line 1; simple one-line data rows start at 2. If using `DictReader.line_num`, remember that physical line numbers differ from logical record numbers when a quoted field spans multiple lines. Explain the convention in output or documentation.

Missing/empty files, invalid headers, malformed CSV, or zero accepted records must never erase a prior valid database import.

### Money rules

- Parse input text directly with `Decimal`.
- Reject non-finite, zero, negative, or not-exactly-representable-to-two-decimal-place amounts.
- Convert to integer paise only after validation; example: `125.50` → `12550`.
- Do not silently round `12.345`.
- `12.340` may be accepted and normalized to `12.34` because it is numerically representable to two decimal places.
- Store/aggregate integer paise; format as rupees only for display.

## 5. Categorization and transaction semantics

- Normalize descriptions by trimming whitespace and converting to lowercase for matching.
- Preserve the original description.
- Use deterministic ordered rules with `rule_id`, pattern, applicable type (`DEBIT`, `CREDIT`, or `ANY`), category, and priority.
- More specific rules must run before broader overlapping rules; first applicable match wins.
- Store both `category` and `rule_id` so the label is explainable.
- Unmatched debits use `Uncategorized`; unmatched credits use `Other Credit`.

Illustrative rule categories from the locked architecture include Transfer, Refund, Income, Dining, Groceries, Subscriptions, and Transport. Patterns are examples for the synthetic dataset, not universal truths about merchants.

### Required totals semantics

- **Total expenses:** DEBIT records excluding records categorized as `Transfer`.
- **Expense by category:** same filter, grouped by category.
- **Credits:** report separately by inferred category.
- **Transfers:** report separately; exclude them from ordinary expense totals and outlier baselines.
- **Refunds:** show as credits in their own category. Do not automatically treat all credits as income or net refunds against original purchases; matching/reconciliation is out of scope.

## 6. SQLite and replacement safety

Use one `transactions` table with the fields and constraints in the locked architecture:

- `id INTEGER PRIMARY KEY`
- `transaction_date TEXT NOT NULL`
- `description TEXT NOT NULL`
- `normalized_description TEXT NOT NULL`
- `transaction_type TEXT NOT NULL CHECK (transaction_type IN ('DEBIT', 'CREDIT'))`
- `amount_paise INTEGER NOT NULL CHECK (amount_paise > 0)`
- `category TEXT NOT NULL`
- `rule_id TEXT NOT NULL`

Use parameterized SQL placeholders (`?`) and `executemany`. Do not build SQL by concatenating input values.

### Required import behavior

1. Read and validate the entire CSV before changing existing data.
2. If there are zero accepted records, leave the existing database data unchanged.
3. Ensure the table exists.
4. Within a database transaction, delete the old rows and insert the newly accepted records.
5. Commit only if the whole replacement succeeds.
6. Roll back on insertion/replacement failure so the prior data remains.
7. Close the connection cleanly.
8. Keep duplicate-looking records within one CSV; they may be legitimate transactions. A successful re-import replaces the previous batch rather than appending to it.

Do not introduce concurrency tuning, WAL configuration, or an ORM.

## 7. Potential-outlier screening

Use a separate baseline for each category, and only include `DEBIT` records that are not categorized as `Transfer`.

For values `x` in one eligible category:

```text
median_x = median(x)
absolute_deviations = [abs(value - median_x) for value in x]
MAD = median(absolute_deviations)
ModifiedZ(value) = 0.6745 * (value - median_x) / MAD
```

- Apply `0.6745` exactly once; use the **raw** MAD.
- Flag only where `abs(ModifiedZ) > 3.5`.
- Require at least five eligible values in a category, including the candidate. This is a project guardrail, not a universal statistical guarantee.
- If too few values: `NOT_EVALUATED_INSUFFICIENT_DATA`.
- If MAD is zero: `NOT_EVALUATED_ZERO_MAD`.
- Never divide by zero or imply that a zero-MAD group has no anomalies.
- Use “potential outlier” or “potentially unusual expense,” never “fraud.” Explain that this is a simple educational screening rule.
- Synthetic data must include at least six debit expenses in one category with an extreme value and a repeated-value category to exercise the zero-MAD path.

## 8. Expected project structure

Keep this structure simple unless the actual repository has a justified, already-approved equivalent:

```text
spendsense/
├── main.py
├── data_processing.py
├── categorization.py
├── storage.py
├── analysis.py
├── data/
│   └── sample_transactions.csv
├── tests/
│   └── test_spendsense.py
├── requirements.txt
├── .gitignore
└── README.md
```

Responsibilities:

- `main.py`: entry point and pipeline orchestration.
- `data_processing.py`: CSV/schema/row validation, date checking, `Decimal`-to-paise conversion.
- `categorization.py`: normalization and ordered category rules.
- `storage.py`: schema initialization, safe transactional replacement, reads and database queries.
- `analysis.py`: SQL summaries and Python Modified Z-score screening.
- `tests/test_spendsense.py`: unit, edge-case, database and end-to-end tests.

Keep functions small and traceable; no class hierarchy is necessary. Follow the locked architecture for the function contracts and results.

## 9. Acceptance checklist — completion is evidence-based

Do not mark the project complete until all applicable checks have actually been run and evidenced.

- [ ] A documented command runs the complete local pipeline.
- [ ] Valid CSV records import correctly.
- [ ] Missing file, empty file and invalid/missing/duplicate headers produce clear errors and preserve the existing dataset.
- [ ] Extra-field and missing-field records are rejected explicitly.
- [ ] Invalid date, amount, description and type have clear row/record rejection reasons.
- [ ] `10.50` becomes `1050` paise; `12.345`, zero, negative, NaN and infinity are rejected.
- [ ] Category rules are deterministic, ordered, and retain `rule_id`.
- [ ] Unknown debit and credit fallbacks are correct.
- [ ] SQL totals match hand-calculated data; credits and transfers are not incorrectly counted as expenses.
- [ ] A valid re-import replaces the prior dataset.
- [ ] An all-invalid import does not erase prior rows.
- [ ] A simulated insert failure rolls back and preserves prior rows.
- [ ] Identical-looking input rows are both retained.
- [ ] Potential-outlier, insufficient-data and zero-MAD paths are tested.
- [ ] End-to-end output is checked against the synthetic sample.
- [ ] README and `.gitignore` are complete.
- [ ] Tests were run locally and the actual result is reported accurately.

A design review passing is **not** proof that implementation works. Never state “all tests pass” without a real test command and output.

## 10. Collaboration protocol for the AI tools

### ChatGPT — main orchestrator and technical guide

ChatGPT should:

- Treat this file and the locked architecture as project context; start each implementation task from the current repository state, not from assumptions.
- Break the work into small, sequential milestones suitable for a beginner and the short deadline.
- Give Antigravity one bounded implementation task at a time, including: objective, allowed files, required behavior, edge cases, acceptance criteria, and exact verification commands.
- Explain important code and design choices in beginner-friendly language and, when asked, explain code line by line.
- Review Antigravity's changed-file summary, diff or relevant code, command output, test output, and remaining issues—not just the agent's claims.
- Decide whether an issue is a blocker, a valid warning, or optional scope. Do not request a validator for every trivial edit.
- Keep a concise current-state record: completed milestone, changed files, tests run/results, known failures, and exact next task.
- Never silently loosen requirements to make tests pass.

### Antigravity IDE — implementation agent

Antigravity should:

- Inspect the actual repository and read this file plus `SpendSense_Final_Architecture_LOCKED_v1_2.md` before editing.
- Implement only the requested milestone; do not rewrite the architecture, rename modules unnecessarily, add dependencies, or implement excluded features.
- Preserve the existing working code and edit only necessary files.
- Make changes in small increments and run the requested checks where possible.
- Report: files inspected, files created/changed, behavior implemented, commands executed, actual test/lint output, failures or unverified items, and any deviation from the architecture.
- Never claim a test passed if it was not run. If unable to run a command, say exactly why.
- Do not commit personal financial data, `.db` files, virtual environments, or caches.

### Gemini or Kimi — independent validator

Use one validator when a checkpoint merits independent review. Avoid running both validators on every small change.

Give the validator the relevant architecture section, changed code/diff (or exact files), test commands and actual output, and a narrow review question. Ask it to:

- Identify correctness bugs, requirement violations, security/data-integrity risks, missing edge cases, and unsupported claims.
- Separate **blockers**, **important issues**, **minor improvements**, and **optional ideas**.
- Cite exact files/functions/lines or quoted code for each finding; explain why it matters and give a minimal fix.
- Check requirements against evidence rather than approving based on the Antigravity report alone.
- Avoid proposing scope expansion or replacing locked decisions without strong cause.
- Give a clear verdict: PASS, CONDITIONAL PASS, or FAIL, with the remaining conditions stated explicitly.

A validator response is a second opinion, not ground truth. ChatGPT should assess whether its findings are correct and relevant before changing the code.

## 11. Recommended work loop

1. **Orient:** ChatGPT identifies the current milestone and reads the architecture/context. Antigravity inspects current files before editing.
2. **Specify:** ChatGPT provides one bounded build prompt with requirements and observable acceptance checks.
3. **Build:** Antigravity implements only that milestone and runs the checks.
4. **Return evidence:** Antigravity reports changed files, relevant diff/code, commands, actual outputs, and unresolved problems.
5. **Decide:** ChatGPT compares evidence with the architecture and decides whether the milestone is complete or requires a focused correction.
6. **Validate at checkpoints:** For important boundaries—CSV validation, transactional database replacement, outlier logic, and end-to-end completion—send the relevant diff and tests to Gemini or Kimi for independent review. Do not relay only a summary if code/test evidence is available.
7. **Correct narrowly:** Fix confirmed issues without broad refactoring. Rerun relevant tests and regression tests.
8. **Checkpoint:** Record status, test evidence, open risks, and the next bounded task. Use Git commits/checkpoints if the repo is under Git and the change is known-good.
9. **Finish:** Run the full test suite, a clean end-to-end demo, and verify the README from a fresh setup as time permits.

### Standard Antigravity report format

Ask Antigravity to return these headings:

1. **Milestone and result** — completed / partial / blocked.
2. **Files changed** — exact paths and purpose.
3. **Implementation details** — brief, factual summary.
4. **Verification run** — exact commands and unedited or faithfully summarized outputs.
5. **Acceptance checklist** — pass/fail/not run, with evidence.
6. **Known issues/deviations** — include anything not matching the locked architecture.
7. **Next smallest action** — propose, do not start unapproved scope.

## 12. Prompt-writing rule for implementation

Every build prompt ChatGPT gives Antigravity should include:

- **Context:** SpendSense and the architecture baseline.
- **Current state:** files/features already confirmed to exist; distinguish known facts from assumptions.
- **Single objective:** one milestone only.
- **Files in scope:** allowed to create/edit, and any files that must not be changed.
- **Exact requirements:** including relevant edge cases from the locked architecture.
- **Acceptance checks:** observable behavior or tests that demonstrate completion.
- **Verification commands:** commands to run and expected type of evidence, without fabricating expected output.
- **Reporting format:** ask for the standard Antigravity report above.
- **Scope guard:** no unrelated refactors, dependencies, architecture changes or optional features.

## 13. Beginner-friendly delivery requirements

The project is also a learning exercise. Prefer readable code over compressed cleverness.

- Explain each module's purpose and how data moves through it.
- Use descriptive variable and function names.
- Add comments for non-obvious logic, not every obvious line.
- Keep error messages useful and specific.
- When teaching code, explain inputs, outputs, important lines, and why the logic is needed.
- Avoid abstractions, design patterns, dependencies, and configuration layers that do not solve a current MVP requirement.
- Do not hide complexity inside a huge `main.py` or create many unnecessary modules.

## 14. Privacy, honesty and presentation

- Use synthetic data in the repository and demo.
- Do not commit personal bank statements, credentials, local SQLite databases, virtual environments or caches.
- Parameterize SQL values.
- Do not claim “fraud detection,” “AI-powered prediction,” production readiness, accuracy improvements, or performance benchmarks.
- Use “potential outlier” / “potentially unusual expense.”
- Distinguish architecture approval from actual implementation and test evidence.
- Record the actual number of accepted/rejected rows and observed test results; never invent them.

## 15. Immediate operating instruction

At the start of a new task, the orchestrator or implementation agent should:

1. Read this project context file.
2. Read the relevant parts of `SpendSense_Final_Architecture_LOCKED_v1_2.md`.
3. Inspect the actual repository and report its current state.
4. Identify the first incomplete acceptance-checklist item or the next logical milestone.
5. Propose or execute only that bounded task.

**Do not restart architecture research, reopen locked decisions, or add optional features unless actual implementation evidence shows a material problem and ChatGPT/user explicitly approves a change.**

---

## Reference links

- Python `csv`: https://docs.python.org/3/library/csv.html
- Python `decimal`: https://docs.python.org/3/library/decimal.html
- Python `sqlite3`: https://docs.python.org/3/library/sqlite3.html
- SQLite transactions: https://www.sqlite.org/lang_transaction.html
- NIST outlier detection: https://www.itl.nist.gov/div898/handbook/eda/section3/eda35h.htm
- pytest: https://docs.pytest.org/en/stable/
