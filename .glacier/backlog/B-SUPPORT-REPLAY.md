# B-SUPPORT-REPLAY — Prevent duplicate support replies during retries and concurrent sends

Owner: Benjamin. Proposed launch card from T-FIND, 2026-10-10. Read [INDEX.md](INDEX.md#launch-contract), AGENTS.md, NORTHSTAR.yaml and ORCHESTRATION.yaml first. Commit on `card/B-SUPPORT-REPLAY`; never push.

## Scope

Allowed edits: `ventures/blocks/customer/__init__.py`. Also allowed: `evidence/backlog/B-SUPPORT-REPLAY/` and a card-specific claim in `vault/claims/`. New ordinary unit tests must live under the affected module’s `tests/unit/` and use this card ID in the filename; no existing test edits. Existing tests, acceptance files and CHECK.md files are read-only. No other paths are authorized.

Exclusive lane: **customer**. Serialize with B-SIGNATURE-AUTH, B-CUSTOMER-RESTORE and B-PAYMENT-STATUS; all share customer/__init__.py.

## Goal and evidence

send_reply calls smtp_sender before recording sent status. A crash or concurrent call could leave ambiguous delivery; current tests mainly exercise approval and recorded sending.

Claim a pending draft atomically, persist its intended message identity, and keep uncertain transport outcomes visible. Require reconciliation rather than blindly sending again after an ambiguous failure.

Read first:

- [ventures/blocks/customer/__init__.py](../../ventures/blocks/customer/__init__.py) (send_reply)

## Drift check

- Checkpoint: **PH12.6**. Properties: **P-LOOPS, P-CONTROL**. Metrics: **M-AUDIT, M-SURVIVE**.
- Dependencies: use the phase ledger in INDEX; assignment permits scoped work, not a phase-exit claim. Recheck dependencies at dispatch; no NORTHSTAR status edits here.
- Existing-tool choice (I-01): SQLite and email message IDs already fit; no mailbox service or custom job engine.
- Value/effort estimate: **4/5 value ÷ 3 effort units = 1.33**. Estimates prioritize impact and unblocking, not promised revenue.

## Verification — specified before implementation

Independent local SMTP/fake transport injects concurrency and failure after acceptance: at most one attempted delivery per approved draft, with auditable pending/sent/uncertain states and no real mail.

Run `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/customer/tests`. Builders first reproduce the defect and have an independent evaluator freeze any missing acceptance case; ordinary unit tests do not substitute for that evaluator. Tester-only cards never repair the product they judge. Follow the launch contract for real-backend proof and final reporting.

Finish with commit hash, changed files, commands/results, fixture versus real evidence, and remaining owner steps. Do not send, publish, sign, file, spend, create accounts, delete owner data or decide legal questions. Use synthetic/local evidence unless an already-authorized read-only source is available.
