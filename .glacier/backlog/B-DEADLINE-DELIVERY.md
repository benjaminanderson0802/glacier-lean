# B-DEADLINE-DELIVERY — Prevent a crash from silently consuming a reminder

Owner: Benjamin. Proposed launch card from T-FIND, 2026-10-10. Read [INDEX.md](INDEX.md#launch-contract), AGENTS.md, NORTHSTAR.yaml and ORCHESTRATION.yaml first. Commit on `card/B-DEADLINE-DELIVERY`; never push.

## Scope

Allowed edits: `ventures/blocks/deadlines/core.py`. Also allowed: `evidence/backlog/B-DEADLINE-DELIVERY/` and a card-specific claim in `vault/claims/`. New ordinary unit tests must live under the affected module’s `tests/unit/` and use this card ID in the filename; no existing test edits. Existing tests, acceptance files and CHECK.md files are read-only. No other paths are authorized.

Exclusive lane: **deadlines**. Block-local reproduction can launch now. Any caller/flow or shared contract change belongs to the integrator after V-AUTOMATE, not this card.

## Goal and evidence

due marks an item fired before the returned Glacier steps are delivered and only matches the exact calendar day. Crash/restart and missed-day behavior need a delivery proof.

Reuse durable runtime facilities to make due reminders recoverable until acknowledged, with stable event identities and a documented late-reminder path. Preserve existing due-call behavior or obtain an integrator contract before an API change.

Read first:

- [ventures/blocks/deadlines/core.py](../../ventures/blocks/deadlines/core.py) (due, glacier_steps)
- [ventures/blocks/deadlines/CHECK.md](../../ventures/blocks/deadlines/CHECK.md)

## Drift check

- Checkpoint: **PH12.5**. Properties: **P-LOOPS**. Metrics: **M-SURVIVE, M-INTERVENE**.
- Dependencies: use the phase ledger in INDEX; assignment permits scoped work, not a phase-exit claim. Recheck dependencies at dispatch; no NORTHSTAR status edits here.
- Existing-tool choice (I-01): Existing DBOS delivery patterns and SQLite transactions; no custom scheduler.
- Value/effort estimate: **5/5 value ÷ 3 effort units = 1.67**. Estimates prioritize impact and unblocking, not promised revenue.

## Verification — specified before implementation

Independent crash injection between selection and delivery must produce one acknowledged reminder after restart, including an overdue date and concurrent consumers. Do not reinterpret legal dates or modify active flows.

Run `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/deadlines/tests`. Builders first reproduce the defect and have an independent evaluator freeze any missing acceptance case; ordinary unit tests do not substitute for that evaluator. Tester-only cards never repair the product they judge. Follow the launch contract for real-backend proof and final reporting.

Finish with commit hash, changed files, commands/results, fixture versus real evidence, and remaining owner steps. Do not send, publish, sign, file, spend, create accounts, delete owner data or decide legal questions. Use synthetic/local evidence unless an already-authorized read-only source is available.
