# SpendSense — Decision Log

**Purpose:** Give the primary agent and specialist subagents a durable record of which decisions are already made, which decisions they may make locally, and which decisions require escalation.  
**Project:** SpendSense — Expense Pattern & Anomaly Detector  
**Current technical baseline:** `SpendSense_Final_Architecture_LOCKED_v1_2.md`  
**Status:** Baseline decisions recorded; no change to the locked architecture is authorized by this log.

---

## 1. Authority and use

Use this file before making a decision that could affect architecture, stored data, user-visible meaning, dependencies, or acceptance criteria.

Authority order:

1. `SpendSense_Final_Architecture_LOCKED_v1_2.md` — authoritative technical requirements.
2. `SpendSense_PROJECT_CONTEXT.md` — project context and locked constraints.
3. `SpendSense_CODE_ARCHITECTURE.md` — module boundaries and function responsibilities.
4. This decision log — records the decisions below and the process for future decisions; it cannot override items 1–3.
5. Existing implementation/tests — evidence of current behavior, not permission to silently change requirements.
6. AI suggestions/reports — advisory only until evaluated against source and evidence.

If the first three project files materially conflict, do not resolve the conflict by guessing. Report the exact conflicting passages and ask the user/ChatGPT to decide. Do not treat a reviewer’s confident tone as authority.

## 2. Decision permission levels

### Level A — Agent may decide autonomously

Allowed when the choice is reversible, local to implementation, and preserves the locked behavior:
- Local variable names, private helper names, and internal formatting.
- A small helper function when it removes duplication and makes code easier to teach.
- Additional focused tests that do not change the contract.
- Clearer exception messages, row-rejection explanations, and comments.
- Small refactors that preserve outputs, public function contracts, and tested behavior.
- README wording and examples that accurately describe the implemented MVP.
- The order of operations within a module when the architecture’s behavior and safety guarantees remain unchanged.

For these choices, select the simplest readable option, state any non-obvious trade-off briefly in the handoff, and do not ask the user to approve routine details.

### Level B — Agent must pause and escalate before deciding

Escalate if the choice changes or may change:
- Any locked requirement, transaction semantic, CSV rule, category rule/precedence, amount parsing rule, outlier eligibility, Modified Z-score formula/threshold/minimum sample size/status, or report meaning.
- The database schema, table count, transaction/rollback strategy, or successful-import replacement behavior.
- A public function’s contract or the intended module dependency direction.
- Runtime or application dependencies, supported Python version, packaging, external APIs, UI/dashboard, deployment, scheduled execution, or other explicit scope exclusions.
- The CSV columns, accepted transaction types, date format, INR/paise model, or what counts as an expense/credit/transfer/refund.
- A destructive action, migration, removal of user data, overwrite of existing user work, or change likely to damage the existing dataset.
- A new feature, a rewrite of working code, or a refactor that materially increases concepts/modules without a demonstrated requirement.
- Any contradiction between source-of-truth documents.

When escalating, present: the decision needed, the exact constraint affected, the viable options (preferably two), the simplest recommendation and why, the risk of each option, and what tests would be needed. Do not implement the disputed choice while waiting.

### Level C — Never decide based on AI confidence alone

Never infer that a test passed without actual command output. Never claim an outlier is fraud. Never assume a CSV is valid because `DictReader` returned a dictionary. Never assume a transaction import is safe because the happy path works. Never accept a validator’s finding without checking whether it is grounded in this codebase and locked specification.

## 3. Locked baseline decisions

These entries are transcribed as operational decisions from architecture v1.2. They are already decided and must not be reopened during normal implementation. A change requires explicit user approval and a reviewed architecture-version update.

### D-001 — Local Python CLI; small educational MVP
- **Status:** LOCKED
- **Decision:** Build a local command-line app for analysis of a documented synthetic transaction CSV.
- **Reason:** Finish a complete, explainable end-to-end data workflow within the time constraint.
- **Implication:** Prioritize correctness, clarity, and a reproducible demo over feature breadth.

### D-002 — Python standard library for application logic
- **Status:** LOCKED
- **Decision:** Python 3.10+; use `csv.DictReader`, `decimal.Decimal`, `sqlite3`, and `statistics.median`; use `pytest` for tests.
- **Reason:** Keep setup and code easy for a beginner to understand.
- **Implication:** Do not add Pandas, an ORM, a machine-learning package, or another application dependency without explicit approval.

### D-003 — Fixed CSV input contract and explicit structural validation
- **Status:** LOCKED
- **Decision:** Use the specified fixed headers and formats in the locked architecture. Validate headers and each record explicitly.
- **Reason:** `csv.DictReader` alone does not guarantee consistent row widths; extra fields can be collected under `restkey`, and missing fields can yield `None` values.
- **Implication:** Detect malformed header/row structure, reserved-`restkey` collisions, malformed values, and `csv.Error` according to v1.2. Keep usable row-level rejection reasons. Treat a file-level parser failure as a failed import and protect the existing database.

### D-004 — Exact money handling as integer paise
- **Status:** LOCKED
- **Decision:** Parse amount text with `Decimal`, reject non-finite/non-positive/unrepresentable values as defined in v1.2, then store integer paise.
- **Reason:** Avoid binary floating-point money errors and keep arithmetic consistent.
- **Implication:** Never parse money through `float`; preserve the exact validation behavior for values such as `12.340` versus `12.345` as specified in the architecture.

### D-005 — Deterministic explainable categorization
- **Status:** LOCKED
- **Decision:** Normalize description text for matching; apply ordered, transaction-type-aware rules; preserve original descriptions and a stable `rule_id`; use required fallback categories.
- **Reason:** Results must be explainable and deterministic.
- **Implication:** Do not add fuzzy classification, learned models, or reorder rules without approval. Test overlapping patterns.

### D-006 — Exact transaction and summary semantics
- **Status:** LOCKED
- **Decision:** Keep DEBIT and CREDIT distinct; exclude transfers from expense totals; report credits separately; apply refund handling and labels exactly as architecture v1.2 defines. Do not net refunds against expenses because matching is out of scope.
- **Reason:** Avoid misleading totals and claims unsupported by the data model.
- **Implication:** Any ambiguity in whether a row contributes to a reported metric must be resolved against v1.2, not guessed.

### D-007 — One SQLite table and atomic dataset replacement
- **Status:** LOCKED
- **Decision:** Use the specified `transactions` table, parameterized SQL, and transactional replacement of the accepted dataset. First validate the input; only replace data after a non-empty valid import; delete and insert inside one transaction; rollback on failure.
- **Reason:** A failed or all-invalid import must not destroy the previous valid dataset.
- **Implication:** No partially replaced table, string-interpolated data SQL, or extra database tables/frameworks. Verify rollback with a failure-path test.

### D-008 — Preserve duplicate-looking rows within an input file
- **Status:** LOCKED
- **Decision:** Do not deduplicate current-import rows merely because their values look identical.
- **Reason:** Identical-looking transactions may be legitimate separate events.
- **Implication:** Re-import replacement semantics do not imply within-file deduplication.

### D-009 — SQL-based summaries
- **Status:** LOCKED
- **Decision:** Use SQLite aggregation (`SUM`, `COUNT`, `GROUP BY`) for expense and category summaries.
- **Reason:** Demonstrate sound relational-data analysis with no DataFrame dependency.
- **Implication:** Keep summary definitions in line with D-006 and the locked SQL behavior.

### D-010 — Category-specific Modified Z-score, carefully bounded
- **Status:** LOCKED
- **Decision:** Use raw MAD and `ModifiedZ = 0.6745 * (value - median) / MAD`; flag only when `abs(score) > 3.5`; evaluate eligible DEBIT expenses by category, excluding transfers, with the v1.2 minimum history guardrail.
- **Reason:** Explainable robust screening for potentially unusual expense values.
- **Implication:** Handle insufficient sample size and zero MAD with the exact not-evaluated statuses. Do not silently substitute another formula, MAD definition, cutoff, category baseline, or candidate eligibility.

### D-011 — Use cautious, non-fraud language
- **Status:** LOCKED
- **Decision:** Describe results as “potential outliers” or “potentially unusual expenses,” never as confirmed fraud.
- **Reason:** The score does not establish wrongdoing or intent.
- **Implication:** Apply the wording to CLI output, README, demo narrative, and comments.

### D-012 — Keep the MVP scope bounded
- **Status:** LOCKED
- **Decision:** Exclude banking APIs, credentials, machine-learning classifiers, recurring-payment detection, dashboards, notifications, cloud deployment, scheduling, multi-currency support, ORM/concurrency tuning, and other out-of-scope features listed in v1.2.
- **Reason:** Protect time, clarity, and completion of the core pipeline.
- **Implication:** Record attractive ideas as future work; do not implement them in the MVP.

### D-013 — Module boundaries and beginner readability
- **Status:** LOCKED
- **Decision:** Follow `SpendSense_CODE_ARCHITECTURE.md` for responsibility separation and one-way dependencies: CLI orchestration, input validation, categorization, storage, and analysis remain distinct.
- **Reason:** Make each part testable and understandable without creating a framework.
- **Implication:** Do not add abstraction layers or circular imports. Keep functions short, named by intent, and explainable line by line.

### D-014 — Evidence-based completion
- **Status:** LOCKED
- **Decision:** A milestone is complete only when its acceptance criteria have evidence from inspected code, actual test/command output, and review of relevant changes.
- **Reason:** Agent summaries can be wrong or incomplete.
- **Implication:** Reports must distinguish `VERIFIED`, `CODE-INSPECTED`, `REPORTED-BUT-UNVERIFIED`, `ASSUMED`, and `UNKNOWN` claims. Do not mark overall completion before the v1.2 definition of done passes.

## 4. Decision-making algorithm for agents

Before implementing a disputed or non-obvious choice, follow this order:

1. **Find the requirement.** Search the locked architecture and code architecture for the relevant rule.
2. **Check this log.** If a matching decision is `LOCKED`, implement it as written.
3. **Classify the choice.** Is it a reversible Level A implementation detail, or a Level B behavior/architecture change?
4. **Choose the smallest correct option.** Prefer standard-library, direct control flow, explicit names, and fewer moving parts.
5. **Add evidence.** Add/update a focused test for behavior that matters.
6. **Recheck safety.** Especially CSV failure paths and SQLite replacement/rollback.
7. **Report accurately.** State the files changed, checks run, results, limitations, and any decision escalations.

If a subagent discovers an apparent conflict, it must report the evidence and not create a new architecture. The primary Antigravity agent consolidates specialist findings; ChatGPT adjudicates whether findings are valid against the locked spec; the user approves any scope or locked-behavior change.

## 5. How to record a future decision

The decision log is append-only in spirit. Do not rewrite historical decisions to hide a previous state. To change one:
1. Ask for user approval when the change falls under Level B.
2. Add a new `D-###` entry instead of silently editing history.
3. Reference the superseded decision ID and record its new status as superseded in a follow-up line.
4. Identify impacted requirements, files, tests, documentation, and risks.
5. Update the architecture only after approval, and update its version/status as appropriate.
6. Run the relevant tests and record actual outcomes.

### Future decision entry template

```markdown
### D-### — Short decision title
- **Status:** PROPOSED | APPROVED | LOCKED | REJECTED | SUPERSEDED
- **Date:** YYYY-MM-DD
- **Requested by / approved by:**
- **Context:** What question has to be resolved?
- **Constraints affected:** Architecture section, decision IDs, module/function contracts.
- **Options considered:**
- **Decision:**
- **Rationale:**
- **Consequences / risks:**
- **Required code/docs/tests:**
- **Evidence after implementation:** Commands and results, or `NOT YET VERIFIED`.
- **Supersedes:** D-### or `None`.
```

## 6. Open decisions

**No new architecture decisions are currently authorized.** The implementation agent should use the locked choices above and make ordinary Level A decisions without slowing down the user. If a real Level B decision emerges, stop only that decision-dependent work, present the smallest useful options, and continue with unrelated safe work only when it does not assume the disputed choice.

---

**End of decision log.**
