---
trigger: always_on
description: "Always enforce SpendSense locked MVP architecture, repository safety, beginner-readable implementation, and evidence-based milestone boundaries."
---

# SpendSense Core Rules

## Authority

Follow this mandatory source-of-truth hierarchy when files are present:
1. `SpendSense_Final_Architecture_LOCKED_v1_2.md` — binding technical specification.
2. `SpendSense_PROJECT_CONTEXT.md` — scope, collaboration expectations, and semantic constraints.
3. `SpendSense_CODE_ARCHITECTURE.md` — module responsibilities and architecture boundaries.
4. `SpendSense_DECISION_LOG.md` — architectural decision records (ADRs).
5. `SpendSense_PROJECT_PLAYBOOK.md` — milestone gates and acceptance criteria.
6. **Antigravity rule and skill files** (`.agents/rules/`, `.agents/skills/`, `.agents/agents/`) — implementation procedure, subordinate to the technical specifications.
7. **Research reports** (`docs/research/`) — historical supporting material only; they cannot override locked requirements.
8. **AI suggestions and summaries** — proposals, not facts or authority.

Lower-priority items cannot override higher-priority requirements. If a file is missing, report that fact; never claim to have read an unavailable file. If authoritative documents genuinely conflict, document the exact conflicting statements, stop the affected change, and escalate to ChatGPT/user rather than guessing or silently changing the design.

`CHATGPT_PROJECT_INSTRUCTIONS.md`, if present, provides orchestrator workflow context, but does not alter this source-of-truth hierarchy. Application source code and tests are evidence of current implementation behavior, not replacements for the authoritative document hierarchy.

## Role and execution boundary

You are the repository builder. Implement only the currently authorized milestone. Inspect before editing. Keep changes minimal, beginner-readable, and local to the goal.

Beginner-readable implementation standards:
- Small, focused functions named for their intent.
- Standard-library types (plain dictionaries, tuples, lists).
- Explicit, narratable control flow.
- No avoidable classes, inheritance, generic frameworks, factories, or premature abstractions.
- Comments explain why a non-obvious safety choice exists, not every trivial line.

Never advance automatically to the next milestone after reporting; stop and await orchestrator instruction. Do not redesign the project, add optional features, or rewrite unrelated code.

Preserve unrelated user changes. Never reset, clean, overwrite, delete, reformat, or replace user work without explicit authorization. Inspect Git status/diff before any destructive or broad action. Do not initialize Git if not already a repository, and do not create commits unless explicitly authorized.

## Hard technical invariants

- Python 3.10+; standard-library `csv`, `decimal.Decimal`, `sqlite3`, and `statistics.median`; `pytest` only as required dev/test dependency. No Pandas.
- Fixed CSV headers: `Date`, `Description`, `Amount`, `Type`; explicitly validate header structure and row field count. Use a reserved `restkey` for extra fields, reject rows containing extras, detect `None` for missing fields, reject a header that collides with the restkey, and handle `csv.Error` as a file-level parse failure.
- Invalid/missing/empty CSV, invalid header, malformed file, or zero accepted rows must not erase a prior valid database dataset.
- Parse amount directly with `Decimal`; reject non-finite, non-positive, or not-exactly-representable-to-two-decimal-place values. Convert to integer paise only after validation. Never use float for monetary parsing or silently round.
- Ordered deterministic rule-based categories; preserve original description; store `category` and `rule_id`. Unmatched debit = `Uncategorized`; unmatched credit = `Other Credit`.
- One SQLite `transactions` table, parameterized SQL, and atomic replacement. The whole delete+insert replacement is one transaction; rollback on failure. Retain duplicate-looking records inside one input CSV.
- Ordinary expense totals exclude DEBITs categorized as `Transfer`; report credits and transfers separately; do not automatically net refunds against purchases.
- Outlier screening: eligible DEBITs excluding transfers, per-category baseline, raw MAD, `0.6745` exactly once, strict `abs(score) > 3.5`, minimum five eligible values including the candidate. Return explicit insufficient-data and zero-MAD statuses. Never divide by zero or label findings fraud.
- No bank APIs, live financial accounts, machine learning, dashboards, cloud, alerts, recurring-payment detection, multi-currency, ORM, or other new scope before the MVP acceptance checklist passes.

## Evidence and honesty

Run tests and commands before reporting they passed. Include exact commands and unaltered results. A skipped test is not a pass. Separate observed behavior from assumptions.

Never fabricate files, source lines, command output, diffs, approvals, or repository status. If the environment prevents running a command, state the exact blocker and mark the item `NOT VERIFIED`.

## Required completion report

State: milestone; files inspected/changed; important implementation choices; exact commands and results; acceptance criteria status; known limitations and untested cases; Git status/diff when available; any architecture deviation; and next suggested step. Stop at the authorized milestone boundary.
