---
name: spendsense-development
description: Use for any SpendSense repository inspection, implementation, debugging, testing, architecture-compliance review, or milestone handoff. Builds the locked MVP in small, evidence-verified steps and keeps the code beginner-readable.
---

# SpendSense Development Workflow Skill

## 1. Mission

Build and verify **SpendSense**, a small local Python CLI that validates a synthetic transaction CSV, categorizes accepted transactions with ordered explainable rules, stores them safely in SQLite, calculates spending summaries using SQL, and screens eligible expenses for potential outliers using the specified Modified Z-score.

The user is learning. Optimize for code that is **correct, simple, explainable, testable, and easy to maintain**—not cleverness, abstraction, or feature count.

## 2. Source of truth and authority

Follow this mandatory source-of-truth hierarchy when files are present:
1. `SpendSense_Final_Architecture_LOCKED_v1_2.md` — binding technical specification.
2. `SpendSense_PROJECT_CONTEXT.md` — scope, collaboration expectations, and semantic constraints.
3. `SpendSense_CODE_ARCHITECTURE.md` — module boundaries and code responsibilities.
4. `SpendSense_DECISION_LOG.md` — architectural decision records (ADRs).
5. `SpendSense_PROJECT_PLAYBOOK.md` — milestone execution and acceptance criteria.
6. **Antigravity rule and skill files** (`.agents/rules/`, `.agents/skills/`, `.agents/agents/`) — implementation procedure, subordinate to the technical specifications.
7. **Research reports** (`docs/research/`) — historical supporting material only; they cannot override locked requirements.
8. **AI suggestions and summaries** — proposals, not facts or authority.

Do not claim to have read a file unless it was actually accessible and read. If a listed file is absent, report that fact and continue using available authoritative material.

The locked v1.2 architecture is the binding technical authority. This skill defines the working method; it does not override technical requirements. Existing code establishes what currently exists, not permission to preserve a defect.

If two authoritative project files materially conflict, identify the exact conflict and stop before making a design-changing edit. Do not silently reinterpret a locked decision.

`CHATGPT_PROJECT_INSTRUCTIONS.md`, if present, provides orchestrator workflow context, but does not alter this source-of-truth hierarchy. Application source code and tests are evidence of current implementation behavior, not replacements for the authoritative document hierarchy.

## 3. Non-negotiable project boundaries

- Use Python 3.10+ and the standard library for application code.
- Use `csv.DictReader`, `decimal.Decimal`, `sqlite3`, and `statistics.median` as specified.
- Use `pytest` for tests; do not add application dependencies without explicit approval.
- Store validated money as integer paise. Never convert text to `float` before validation.
- Keep one SQLite `transactions` table and replace the imported dataset atomically after a successful, non-empty validation result.
- Use SQL aggregation for expense/category summaries.
- Use category-specific Modified Z-scores with **raw MAD**, factor `0.6745` exactly once, and flag only when `abs(score) > 3.5`.
- Handle insufficient category history and zero MAD explicitly.
- Say “potential outlier” or “potentially unusual expense,” never “fraud.”
- Preserve legitimate duplicate-looking rows within the same CSV.
- Do not add Pandas, dashboards, APIs, ML, recurrence detection, cloud services, ORM, concurrency tuning, or other excluded features.
- Do not change locked schemas, transaction semantics, thresholds, dependencies, or input rules without the user's explicit approval.

## 4. Work in bounded milestones

Use the first incomplete milestone supported by the actual repository state. Do not rebuild functioning work merely to make the tree look like a template.

### Milestone 0 — Inspect current truth

When starting fresh, when context is missing, or when asked to inspect:

1. Check the repository root and file structure.
2. Read the relevant instructions and architecture.
3. Inspect `git status` and diffs if Git is available.
4. Inspect existing source and tests before proposing edits.
5. Determine Python/pytest availability with actual commands when possible.
6. Separate verified facts from reports, assumptions, and unknowns.

If the user requested inspection only, make no file changes. Report the current state and wait.

### Milestone 1 — CSV structure, row validation, and money

Implement only the input boundary first. Check required, duplicate, missing, and unsupported headers; reserved `restkey` collision; row extra fields and missing fields; `csv.Error`; date; non-empty description; `DEBIT`/`CREDIT`; `Decimal`; and paise conversion.

`DictReader` does not automatically raise for missing/extra row fields. Explicitly detect a dedicated `restkey` such as `__EXTRA_COLUMNS__` and required-field values of `None`. Test valid records before and after malformed records. Missing files, empty input, invalid headers, parser errors, and zero accepted rows must not erase a prior database dataset.

Test at least: `10.50`, `12.340`, `12.345`, zero, negative, NaN, infinity, invalid dates, blank descriptions, invalid types, extra columns, missing columns, and unreadable/missing files.

### Milestone 2 — Explainable categorization

Implement normalization and prioritized rules. Preserve the original description, use deterministic order, apply transaction-type scope, and retain a `rule_id`. Test overlapping patterns and fallbacks (`Uncategorized` for debit; `Other Credit` for credit). Do not add fuzzy matching or machine learning.

### Milestone 3 — SQLite and safe replacement

Implement the locked table schema, parameterized SQL, and `executemany`. First validate the complete input. If no records are accepted, leave existing database contents unchanged. During replacement, delete and insert in one transaction; commit only on success and roll back on failure. Test first import, successful replacement, repeated import, identical rows, all-invalid input, and simulated insertion failure.

### Milestone 4 — Summaries and outlier screening

Use SQL `SUM`, `COUNT`, and `GROUP BY` for summaries. Keep expenses, credits, refunds, and transfers distinct according to the locked semantics. For outliers, use eligible DEBIT expenses only, exclude transfers, create a separate baseline per category, require at least five observations including the candidate, handle zero MAD, and apply the raw-MAD Modified Z-score formula exactly as specified.

### Milestone 5 — CLI integration and end-to-end behavior

Connect the validated CSV, categorization, storage, summary, outlier, and reporting functions. Print accepted/rejected counts and useful reasons; totals; category totals; separately labelled credits/transfers; outliers; and not-evaluated statuses. Do not include needlessly sensitive values in rejection logs.

### Milestone 6 — Tests, documentation, and demo

Run focused tests after changes and the full suite at completion. Ensure the sample CSV contains an eligible category with an obvious extreme amount and a repeated-value category for the zero-MAD case. Complete the README and `.gitignore`. Test the documented command and inspect the actual output.

## 5. Canonical operating loop for every implementation task

Follow this 13-step canonical loop for every implementation milestone:

1. **Establish actual repository state:** Inspect directory structure, existing source, tests, and uncommitted changes before planning.
2. **Read the relevant authoritative documents:** Follow the source-of-truth hierarchy (Section 2) for all binding rules.
3. **Identify the smallest unfinished acceptance-gate item:** Focus exclusively on the single next milestone authorized by the playbook.
4. **Write one bounded implementation plan:** Detail the target files, requirements, test commands, and non-goals.
5. **Implement only the authorized milestone:** Keep changes local, minimal, and beginner-readable. Never start the next milestone.
6. **Inspect the actual diff and relevant source:** Verify that no unrelated files or user work were disturbed.
7. **Run focused tests and the full suite when appropriate:** Execute unit tests first, followed by regression tests.
8. **Collect exact commands and unaltered test results:** Record actual command invocations, exit codes, and output.
9. **Self-audit against the locked requirements:** Check failure handling, data preservation, and boundary invariants.
10. **Request independent Gemini validation at high-risk checkpoints when available:** Submit source excerpts, diffs, and test output.
11. **Adjudicate findings against source and reproducible evidence:** Filter false positives, confirm real defects, and implement minimal fixes.
12. **Report PASS, FAIL, CONDITIONAL, or NOT VERIFIED:** Provide the required handoff report with concrete evidence.
13. **Stop and wait for the orchestrator's next instruction:** Do not proceed to the next milestone automatically.

### Required implementation prompt specification

Every milestone prompt provided by the orchestrator must specify:
1. **Milestone and goal:** Exact milestone number, title, and bounded objective.
2. **Required documents to read:** Specific authoritative documents to inspect before editing.
3. **Initial state inspection:** Required checks on existing code and repository state.
4. **Allowed files and scope:** Explicit list of files that may be created or modified.
5. **Locked constraints and prohibited changes:** Explicitly forbidden scope, libraries, or architectural modifications.
6. **Required behavior and edge cases:** Specific input conditions, boundary values, and error behaviors.
7. **Exact tests and commands:** Required pytest commands and verification steps.
8. **Acceptance criteria:** Explicit pass/fail matrix criteria.
9. **Evidence/report format:** Required structure of the completion report.
10. **Explicit stop condition:** Mandate to halt and wait for review before advancing.

### Beginner-readable implementation standards

- Prefer descriptive names, straightforward control flow, small functions, and plain dictionaries/tuples/lists.
- Add comments to explain non-obvious reasoning and safety guarantees, not to narrate trivial syntax.
- Avoid unnecessary classes, inheritance, generic frameworks, factories, or premature abstractions.
- Keep each function's input, output, and failure behavior explicit and narratable.
- Do not weaken or delete a valid test to obtain a passing suite.

## 6. Evidence and status language

Use these labels accurately:

- **VERIFIED** — directly checked in the repository or by an executed command/test.
- **OBSERVED IN CODE** — visible in inspected code, but runtime behavior has not been proven.
- **REPORTED** — stated by another agent/user but not independently checked here.
- **NOT VERIFIED** — unknown or could not be checked.
- **DEVIATION** — actual behavior differs from a locked requirement.

For every important test, distinguish `PASS`, `FAIL`, and `NOT RUN`. Never claim that a test ran unless it did. Never fabricate files, source lines, command output, diffs, approvals, or repository status.

## 7. Multi-agent handoff and independent validation

SpendSense coordinates multiple AI agents with distinct roles:
- **ChatGPT:** Main orchestrator, technical decision-maker, prompt author, and reviewer.
- **Antigravity:** Repository inspection, implementation, testing, and evidence collection.
- **Gemini:** Independent validator at designated high-risk checkpoints when available.
- **Kimi:** Optional fallback *only* when Gemini is unavailable or a material disagreement remains.

### Canonical handoff chain

`ChatGPT (Orchestrator) → Antigravity (Builder) → Gemini (Validator, when appropriate) → ChatGPT (Decision)`

1. **Orchestration to Builder:** ChatGPT provides a bounded implementation prompt meeting the specification above.
2. **Builder Execution:** Antigravity inspects, implements, executes tests, and collects unaltered evidence.
3. **Validation Handoff:** At high-risk checkpoints, Antigravity provides:
   - The relevant locked requirement and decision ID.
   - The actual changed code lines or Git diff.
   - The exact test command and unaltered execution output.
   - A narrow, specific review question.
   *(A prose summary alone is never acceptable for high-risk reviews).*
4. **High-Risk Validation Checkpoints:**
   - Milestone 1: CSV header checking, `csv.Error`, row isolation, and Decimal money conversion.
   - Milestone 3: SQLite schema constraints, parameterized SQL, atomic replacement, and rollback safety.
   - Milestone 4: SQL summary semantics, transfer exclusion, and Modified Z-score outlier calculations.
   - Milestone 5/6: CLI integration, end-to-end command output, and README consistency.
5. **Validator Rules & Fallback:**
   - The validator must separate confirmed defects from hypotheses, cite exact code lines, and classify findings using standard classifications.
   - If Gemini is unavailable, report that fact honestly. Never fabricate a Gemini approval or silently substitute another validator.
   - Continue without Gemini only when the orchestrator's workflow explicitly permits it.
   - Use Kimi solely as the designated fallback when Gemini is unavailable or when a material disagreement requires secondary adjudication.
6. **Orchestrator Decision:** ChatGPT reviews findings and evidence, authorizes fixes if needed, or issues the prompt for the next milestone. Antigravity never self-advances.

## 8. Git and preservation rules

If Git is available:

- inspect `git status` before changes;
- preserve pre-existing user changes;
- review `git diff` after changes;
- checkpoint only after the milestone is verified, if the user/workflow permits commits;
- do not reset, clean, discard, or overwrite user work without understanding the impact and obtaining permission when needed.

Never commit real personal financial transactions, credentials, database files, virtual environments, or caches. Use synthetic sample data.

## 9. Required handoff report

End every milestone with this compact report:

1. **Milestone/status:** `PASS`, `NEEDS FIXES`, `BLOCKED`, or `PARTIAL`.
2. **Files changed:** exact paths and purpose; say “none” if inspection-only.
3. **What changed:** concise explanation of actual implementation.
4. **Verification:** exact commands run and actual results.
5. **Acceptance criteria:** `PASS` / `FAIL` / `NOT VERIFIED`, with evidence.
6. **Known issues:** skipped tests, limitations, assumptions, or deviations.
7. **Git state:** relevant status/diff/checkpoint if available.
8. **Next action:** recommend one next step; do not start it automatically.

If no files were modified, make that explicit. If code is not runnable yet, say so instead of manufacturing success.

## 10. Completion gate

The project is done only when the locked architecture's acceptance requirements have been checked against the actual implementation, the full test suite has a recorded result, a synthetic-data end-to-end run has been inspected, and the README's setup/run/test instructions are credible. Explicitly list anything blocked or not verified.

Do not claim production readiness, bank integration, fraud detection, predictive AI, or measured performance improvements. The deliverable is a small, explainable educational MVP.

**Operating rule:** Inspect the real state. Build one small milestone. Prove it with evidence. Correct confirmed problems. Report honestly. Stop and wait before starting the next milestone.
