# B-FILER-RECOVERY — Avoid re-filing when a portal succeeds before the local receipt is saved

Owner: Benjamin. Proposed launch card from T-FIND, 2026-10-10. Read [INDEX.md](INDEX.md#launch-contract), AGENTS.md, NORTHSTAR.yaml and ORCHESTRATION.yaml first. Commit on `card/B-FILER-RECOVERY`; never push.

## Scope

Allowed edits: `ventures/blocks/filer/portal.py; ventures/blocks/filer/runner.mjs`. Also allowed: `evidence/backlog/B-FILER-RECOVERY/` and a card-specific claim in `vault/claims/`. New ordinary unit tests must live under the affected module’s `tests/unit/` and use this card ID in the filename; no existing test edits. Existing tests, acceptance files and CHECK.md files are read-only. No other paths are authorized.

Exclusive lane: **filer**. Serialize after B-FILER-SETUP and B-FILER-BINDING. Local mock only; real filings remain owner/customer actions.

## Goal and evidence

The local confirmation transaction occurs after browser submission. The existing replay proof covers saved receipts, not a crash after the external side effect.

Persist operation intent and distinguish confirmed, not-submitted and unknown outcomes. Recover a portal receipt where possible; otherwise require reconciliation and never automatically repeat an uncertain submission.

Read first:

- [ventures/blocks/filer/portal.py](../../ventures/blocks/filer/portal.py) (submit)
- [ventures/blocks/filer/CHECK.md](../../ventures/blocks/filer/CHECK.md)

## Drift check

- Checkpoint: **PH12.7**. Properties: **P-LOOPS, P-CONTROL**. Metrics: **M-SURVIVE, M-AUDIT**.
- Dependencies: use the phase ledger in INDEX; assignment permits scoped work, not a phase-exit claim. Recheck dependencies at dispatch; no NORTHSTAR status edits here.
- Existing-tool choice (I-01): Existing SQLite transaction log and portal confirmation; do not promise distributed exactly-once execution.
- Value/effort estimate: **5/5 value ÷ 3 effort units = 1.67**. Estimates prioritize impact and unblocking, not promised revenue.

## Verification — specified before implementation

Independent mock portal counts submissions while terminating the owned client immediately after the mock side effect; restart/retry must not produce a second filing and must expose the unknown outcome until reconciled.

Run `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/filer/tests`. Builders first reproduce the defect and have an independent evaluator freeze any missing acceptance case; ordinary unit tests do not substitute for that evaluator. Tester-only cards never repair the product they judge. Follow the launch contract for real-backend proof and final reporting.

Finish with commit hash, changed files, commands/results, fixture versus real evidence, and remaining owner steps. Do not send, publish, sign, file, spend, create accounts, delete owner data or decide legal questions. Use synthetic/local evidence unless an already-authorized read-only source is available.
