# SpendSense — Project Playbook

**Purpose:** This playbook is the practical operating manual for building, testing, validating, and presenting the SpendSense MVP. It defines the execution sequence and the AI handoff loop. It does not replace the locked technical specification.

## 1. Project identity and goal

SpendSense is a local Python command-line application that analyses a synthetic expense CSV. It validates records, applies deterministic and explainable category rules, stores accepted records in SQLite, calculates summaries with SQL, and screens eligible debit expenses for potential outliers using a category-specific Modified Z-score.

The deliverable is a small, complete, tested, beginner-explainable project—not a full financial product.

## 2. Source-of-truth order

When documents, code, or AI suggestions disagree, use this order:

1. `SpendSense_Final_Architecture_LOCKED_v1_2.md` — exact technical requirements and locked decisions.
2. `SpendSense_PROJECT_CONTEXT.md` — project orientation, non-negotiables, and tool responsibilities.
3. `SpendSense_PROJECT_PLAYBOOK.md` — implementation stages, review gates, and handoffs.
4. `SpendSense_SYSTEMATIC_WORKFLOW.md` — additional workflow detail and report templates; retain as a supporting reference.
5. Repository code and tests — evidence of what currently exists, but not permission to silently violate the architecture.
6. ChatGPT, Antigravity, Gemini, or Kimi suggestions — recommendations to evaluate, not automatic authority.

If a requirement appears ambiguous, contradictory, or impossible, stop and describe the conflict. Do not silently change the locked architecture. Ask the user/ChatGPT to decide.

## 3. Roles and boundaries

### ChatGPT — main orchestrator and tutor

- Select one milestone at a time.
- Write a focused Antigravity prompt with the goal, permitted scope, edge cases, and acceptance gate.
- Review Antigravity's evidence and relevant code changes.
- Explain code in beginner-friendly language when the user asks or when a new concept is introduced.
- Review independent validator findings and decide which ones are valid.
- Decide whether the milestone passes or needs a focused correction.

### Antigravity — repository builder

- Inspect actual files before editing.
- Implement only the current milestone.
- Keep changes minimal and beginner-readable.
- Run the relevant tests and include actual command output.
- Report all touched files, known issues, skipped tests, and architecture deviations.
- Never claim a test passed unless it was actually run.
- Stop after reporting; do not start the next milestone unless instructed.

### Gemini OR Kimi — independent validator

- Validate important checkpoints, not every tiny edit.
- Review actual diffs/code plus test outputs and the locked architecture.
- Separate confirmed defects from hypotheses and unverified claims.
- Suggest minimal corrections rather than proposing a new architecture.
- Do not be treated as a build executor unless it actually has access to the repository and has run the commands.

### User — project owner

- Keep the project folder and Git checkpoints safe.
- Paste Antigravity reports and relevant diffs/test results back into ChatGPT.
- Approve any proposed change to the locked design or scope.

## 4. The standard work loop

Repeat this loop for every milestone:

1. **Orient:** ChatGPT and Antigravity read the locked architecture, project context, and this playbook. Antigravity inspects the actual repository and Git status.
2. **Plan one milestone:** ChatGPT provides a prompt limited to one goal. It states likely files, mandatory behavior, failure cases, tests, and the pass gate.
3. **Implement:** Antigravity inspects the current implementation, makes the smallest necessary change, and avoids unrelated refactors.
4. **Test:** Antigravity runs focused tests first, then broader tests when appropriate. It includes exact commands and actual output.
5. **Handoff:** Antigravity returns the required milestone report and relevant code diff or excerpts. The user pastes this into ChatGPT.
6. **Review:** ChatGPT checks the evidence against the architecture and tests, not just the narrative report.
7. **Independent check when warranted:** For high-risk gates, pass the relevant diff, exact specification, and test output to Gemini or Kimi. Do not paste only Antigravity's summary.
8. **Adjudicate:** ChatGPT assesses each validator finding. Confirmed defects get a targeted correction prompt; speculative or irrelevant suggestions are not blindly implemented.
9. **Checkpoint:** After a passing milestone, inspect `git diff`, run tests, and create a Git commit if Git is available and the working tree is safe.
10. **Advance:** Move to the next milestone only after the acceptance gate passes. Never mark work complete based only on an AI assertion.

## 5. Locked technical rules

These are not to be changed without explicit approval:

- Python 3.10+.
- Standard-library `csv.DictReader`, `decimal.Decimal`, `sqlite3`, and `statistics.median` for application logic.
- `pytest` is the only required development/test dependency.
- No Pandas in this MVP.
- One fixed synthetic CSV schema: `Date`, `Description`, `Amount`, `Type`.
- Date is a real calendar date in `YYYY-MM-DD` format.
- Amount is positive INR decimal text. Parse directly with `Decimal`; reject non-finite values and values not exactly representable to two decimal places. Convert to integer paise only after validation; never parse via `float` or silently round.
- Type is normalized to `DEBIT` or `CREDIT`.
- CSV structural row issues are explicit: configure a reserved `restkey` for extra fields, detect rows with extra values, detect `None` required fields for missing fields, and reject invalid/ambiguous headers. Handle `csv.Error` as a file-level parse failure.
- Missing file, empty input, invalid header, malformed input, or zero accepted records must not erase the prior valid database dataset.
- Ordered substring categorization rules must be deterministic and explainable; save `category` and `rule_id`; keep original descriptions.
- Unmatched debit: `Uncategorized`. Unmatched credit: `Other Credit`.
- Store accepted transactions in one SQLite `transactions` table; parameterized SQL only; use atomic dataset replacement.
- A successful valid import replaces prior imported records rather than appending. Preserve identical-looking rows within the current CSV; do not deduplicate them.
- Total expenses and expense-by-category summaries exclude records categorized as `Transfer`; credits are reported separately. Do not automatically net refunds against purchases.
- Outlier screening includes only DEBIT records that are not `Transfer`, uses a separate category baseline, raw MAD, `0.6745` exactly once, and strict `abs(score) > 3.5`.
- Require at least five eligible records per category including candidate. Return `NOT_EVALUATED_INSUFFICIENT_DATA` for smaller groups and `NOT_EVALUATED_ZERO_MAD` when raw MAD is zero. Never divide by zero.
- Describe results as **potential outliers** or **potentially unusual expenses**, never as fraud.
- No APIs/bank credentials, machine learning, dashboards, cloud, alerts, recurring payments, multi-currency, ORM, server database, or optional features before the full acceptance checklist passes.

## 6. Milestone roadmap and pass gates

### Milestone 0 — Repository inspection only

**Purpose:** Learn what already exists without disturbing it.

Inspect project structure, current Git status, Python version, pytest availability, existing source, and existing tests. Run tests only if safe and do not overwrite user changes. Mark each later milestone as complete, incomplete, or not assessable based on evidence.

**Pass gate:** An accurate inspection report is returned; no files were modified.

### Milestone 1 — CSV schema validation and money parsing

**Likely files:** `data_processing.py`, tests.

Build or verify `load_and_validate_csv(path)` and `to_paise(amount_text)`. Validate headers, record shape, date, description, amount, and type. Return accepted records plus rejected records with record/line reference and concise reason. Continue after individual invalid records when the CSV parser can safely continue. Catch file-level failures.

Test valid rows before and after malformed rows, extra fields, missing fields, missing/duplicate/unexpected headers, invalid calendar dates, empty descriptions, bad types, missing files, empty CSV, `10.50` → `1050`, and rejected `12.345`, zero, negative, NaN, and infinity. Check `12.340` is normalized consistently with the architecture.

**Pass gate:** Focused tests prove row validation and money conversion. Existing database state must not be touched by this stage.

### Milestone 2 — Deterministic categorization

**Likely files:** `categorization.py`, tests.

Normalize by trimming and lowercasing for matching but retain the original description. Implement ordered rules with `rule_id`, pattern, applicable type, category, and priority. More specific overlapping rules come before broader rules. Keep fallback labels as specified.

Test overlap/priority, transaction-type restrictions, transfer/refund/income handling, unknown debit/credit fallbacks, case/whitespace normalization, and `rule_id` values.

**Pass gate:** Same input always produces the same category and rule ID; tests prove priority and type constraints.

### Milestone 3 — SQLite schema and atomic replacement

**Likely files:** `storage.py`, tests.

Implement `initialize_database`, `replace_transactions`, and `read_transactions`. Create the single required transactions table and constraints. Use parameter placeholders and `executemany`. Read and validate the CSV before changing the database. Do not replace the existing dataset when zero records are accepted. Delete old rows and insert new rows in one transaction; commit only if all inserts succeed; rollback on failure.

Test first import, re-import replacement, identical rows retained, all-invalid import preserves old records, missing/invalid file preserves old records, and simulated insert failure rollback.

**Pass gate:** All data preservation and rollback tests pass on temporary database paths.

### Milestone 4 — SQL summaries and potential-outlier screening

**Likely files:** `analysis.py`, possibly read/query helpers in `storage.py`, tests.

Use SQL `SUM`, `COUNT`, and `GROUP BY` for summaries. Exclude transfers from expense totals, report credits independently, and do not net refunds. Implement category-specific Modified Z-scores from raw MAD in standard-library Python.

Test hand-computed totals, transfer/refund semantics, eligible debit-only baseline, extreme synthetic candidate flagged under the threshold, insufficient history, zero MAD, and no division-by-zero errors.

**Pass gate:** Summary totals match manually verified figures; all specified anomaly guardrails pass.

### Milestone 5 — CLI end-to-end integration

**Likely files:** `main.py`, modules, sample CSV, tests.

Wire validation, categorization, database replacement, summaries, outlier screening, and terminal output into one documented local command. The report includes import counts, rejections and reasons, expense/category totals, credit/transfer totals, potential outliers, and not-evaluated reasons. Amounts are displayed from integer paise as rupees. Avoid exposing unnecessary full rejected-row contents.

**Pass gate:** Run the documented command against synthetic sample data, inspect database contents where useful, and run the full test suite. Compare the output with hand-checked expected results.

### Milestone 6 — Documentation and final demo

**Likely files:** `README.md`, `requirements.txt`, `.gitignore`, tests/sample data if required.

Document purpose, synthetic-data limitation, input schema, setup, run command, test command, replacement semantics, categories, outlier rule, limitations, and demo steps. Keep runtime logic standard-library-only. `requirements.txt` should list pytest only unless the locked architecture is explicitly changed.

**Pass gate:** A fresh user can set up, run, and test the app by following the README. Every acceptance criterion has evidence. Save a final Git checkpoint if available.

## 7. Standard Antigravity prompt template

ChatGPT should customize this for one milestone at a time. Antigravity should not execute a future milestone early.

```text
Project: SpendSense — Expense Pattern & Anomaly Detector.

Before editing, read:
- SpendSense_Final_Architecture_LOCKED_v1_2.md
- SpendSense_PROJECT_CONTEXT.md
- SpendSense_PROJECT_PLAYBOOK.md

CURRENT MILESTONE:
[One milestone only]

OBJECTIVE:
[One observable outcome]

FIRST:
Inspect the current relevant code, tests, and Git status. Preserve existing work.

SCOPE:
[Files/functions allowed to change]

REQUIREMENTS:
[Exact requirements from the locked architecture]

EDGE CASES:
[Relevant normal, invalid, and failure inputs]

ACCEPTANCE GATE:
[Observable tests/results required to pass]

TEST COMMANDS:
[Focused tests and any required manual run]

CONSTRAINTS:
- Do not change locked architecture or add features/dependencies.
- Avoid unrelated edits and refactors.
- Keep code modular, simple, and explainable to a beginner.
- Never claim a command or test was executed unless it was.
- If blocked or a locked requirement seems contradictory, stop and report the issue.
- Do not start the next milestone automatically.

Return the milestone report required by SpendSense_PROJECT_PLAYBOOK.md.
```

## 8. Required Antigravity milestone report

Antigravity must return these sections after each milestone:

1. **Milestone and status:** `PASS`, `BLOCKED`, or `NEEDS FIXES`, plus reason.
2. **Files changed:** exact paths and why.
3. **Implementation summary:** what actually changed.
4. **Evidence:** exact commands executed and actual output/result; show relevant test summary.
5. **Acceptance gate:** pass/fail/not run for each criterion, with evidence.
6. **Known issues:** bugs, assumptions, skipped tests, and environment problems.
7. **Architecture compliance:** any deviation; state “none identified” only after checking.
8. **Git checkpoint:** commit hash if created, or why not.
9. **Next recommended action:** one action only. Stop and wait for further instruction.

If the report is long, provide the relevant diff or exact snippets for critical logic. A summary alone is not sufficient evidence for risky CSV, money, or database behavior.

## 9. Independent validator protocol

Use Gemini **or** Kimi at major checkpoints: CSV structural validation and money parsing; atomic SQLite replacement; summary semantics and Modified Z-score; final end-to-end check. Usually skip for formatting or trivial comments.

Give the validator:
- the relevant excerpt from `SpendSense_Final_Architecture_LOCKED_v1_2.md`;
- the code diff or actual relevant files;
- the exact commands run and complete relevant test output;
- the Antigravity report, as context only.

Validator prompt:

```text
Act as a skeptical independent code reviewer for SpendSense. Treat SpendSense_Final_Architecture_LOCKED_v1_2.md as the specification. Review the actual code/diff and test output, not just the builder's narrative.

Check only this milestone and related regressions. For each finding, state severity (BLOCKER/HIGH/MEDIUM/LOW), evidence, consequence, and the smallest correction. Separate confirmed defects from hypotheses and list any claims unsupported by test output. Do not invent execution results, add features, or redesign locked choices. If you cannot execute the code, say so. A clean limited review is not proof the entire project is correct.
```

After validation, paste both the validator's response and Antigravity's related code/test evidence into ChatGPT. ChatGPT must adjudicate findings before changes are made. Do not implement every suggestion automatically.

## 10. Git and change safety

- Check `git status` before changes.
- Do not discard pre-existing user changes.
- Review `git diff` before checkpoint commits.
- After a passed milestone, run the relevant tests before committing.
- If a change breaks a passing milestone, inspect the diff and recover carefully; do not run destructive reset/clean commands without explicit user approval and understanding what would be lost.
- Use short, milestone-specific commits where available, e.g. `feat: validate CSV transactions`, `feat: add categorization rules`, `feat: replace SQLite imports atomically`, `feat: add summaries and outlier screening`, `test: verify end-to-end pipeline`, `docs: add setup and demo instructions`.

## 11. Beginner-friendly standard

Keep functions small and names descriptive. Avoid clever abstractions, class hierarchies, and unnecessary configuration layers. Explain unfamiliar code in simple language when presenting it to the user, including input, output, why the logic is needed, and a small example. Do not dump unrelated code all at once when a milestone-sized change is enough.

## 12. Definition of done

SpendSense is done only when all of these are demonstrated:

- One documented command runs the complete pipeline locally.
- Fixed-schema CSV accepted and invalid records rejected with clear record references and reasons.
- Decimal money validation and integer-paise storage are correct.
- Categorization is deterministic and explainable with `rule_id`.
- SQLite contains accepted records and atomic replacement safety is demonstrated.
- SQL expenses/category summaries match hand calculations and correctly distinguish credits/transfers/refunds.
- Modified Z-score follows the locked formula and handles insufficient data and zero MAD safely.
- Terminal output says “potential outlier,” not fraud.
- Synthetic data covers normal operation, extreme outlier, zero MAD, and validation failures.
- Automated tests pass and the actual command/output are recorded.
- README, `requirements.txt`, and `.gitignore` are complete.
- Final diff has no unrelated changes and no unresolved blocker remains.

Do not claim “complete” until the actual repository and test evidence support every applicable item.
