# B-CUSTOMER-RESTORE — Make customer records recoverable without the original SQLite database

Owner: Benjamin. Proposed launch card from T-FIND, 2026-10-10. Read [INDEX.md](INDEX.md#launch-contract), AGENTS.md, NORTHSTAR.yaml and ORCHESTRATION.yaml first. Commit on `card/B-CUSTOMER-RESTORE`; never push.

## Scope

Allowed edits: `ventures/blocks/customer/__init__.py; new ventures/blocks/customer/recovery.py`. Also allowed: `evidence/backlog/B-CUSTOMER-RESTORE/` and a card-specific claim in `vault/claims/`. New ordinary unit tests must live under the affected module’s `tests/unit/` and use this card ID in the filename; no existing test edits. Existing tests, acceptance files and CHECK.md files are read-only. No other paths are authorized.

Exclusive lane: **customer**. Exclusive customer lane; coordinate read-only use of E-PH4 memory APIs. API changes are outside this card.

## Goal and evidence

Customer accounts, support drafts and audit records are stored in SQLite; the documented record path does not demonstrate reconstruction from readable versioned files.

Add a private local plain-file event/export path using existing vault facilities so essential customer state and linked signature artifacts can be restored. Keep credentials excluded and honor retention; never commit customer PII to the project repository.

Read first:

- [ventures/blocks/customer/README.md](../../ventures/blocks/customer/README.md)
- [ventures/blocks/customer/__init__.py](../../ventures/blocks/customer/__init__.py)
- [NORTHSTAR.yaml](../../NORTHSTAR.yaml) (I-06)

## Drift check

- Checkpoint: **PH12.6**. Properties: **P-MEMORY, P-CONTROL**. Metrics: **M-RECOVER, M-AUDIT**.
- Dependencies: use the phase ledger in INDEX; assignment permits scoped work, not a phase-exit claim. Recheck dependencies at dispatch; no NORTHSTAR status edits here.
- Existing-tool choice (I-01): Existing vault/git APIs and SQLite rebuild; no new memory database or backend edits.
- Value/effort estimate: **4/5 value ÷ 3 effort units = 1.33**. Estimates prioritize impact and unblocking, not promised revenue.

## Verification — specified before implementation

Independent synthetic purchase/support/signature records survive an isolated database rebuild with identical identifiers, statuses and audit links. Corrupt/missing exports fail closed; deleted-by-policy content is not resurrected.

Run `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/customer/tests`. Builders first reproduce the defect and have an independent evaluator freeze any missing acceptance case; ordinary unit tests do not substitute for that evaluator. Tester-only cards never repair the product they judge. Follow the launch contract for real-backend proof and final reporting.

Finish with commit hash, changed files, commands/results, fixture versus real evidence, and remaining owner steps. Do not send, publish, sign, file, spend, create accounts, delete owner data or decide legal questions. Use synthetic/local evidence unless an already-authorized read-only source is available.
