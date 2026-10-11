# B-FEED-QUARANTINE — Keep suspect source updates out of trusted feed snapshots

Owner: Benjamin. Proposed launch card from T-FIND, 2026-10-10. Read [INDEX.md](INDEX.md#launch-contract), AGENTS.md, NORTHSTAR.yaml and ORCHESTRATION.yaml first. Commit on `card/B-FEED-QUARANTINE`; never push.

## Scope

Allowed edits: `ventures/blocks/feeds/core.py`. Also allowed: `evidence/backlog/B-FEED-QUARANTINE/` and a card-specific claim in `vault/claims/`. New ordinary unit tests must live under the affected module’s `tests/unit/` and use this card ID in the filename; no existing test edits. Existing tests, acceptance files and CHECK.md files are read-only. No other paths are authorized.

Exclusive lane: **feeds**. No active-card edits; RG-RECALL reads this block. Preserve its public API and integrate only after its existing consumers pass.

## Goal and evidence

sync adds canary/count/schema alerts but still calls store_snapshot; normalize_rows also changes the remembered schema before release validation.

Quarantine incomplete or incompatible candidates while preserving the last validated rows and schema. Return a visible failed-refresh result; distinguish a first import without a trusted snapshot.

Read first:

- [ventures/blocks/feeds/core.py](../../ventures/blocks/feeds/core.py) (normalize_rows, sync, store_snapshot)
- [ventures/blocks/feeds/CHECK.md](../../ventures/blocks/feeds/CHECK.md)

## Drift check

- Checkpoint: **PH12.5**. Properties: **P-VERIFY, P-LOOPS**. Metrics: **M-FALSE-DONE, M-SURVIVE**.
- Dependencies: use the phase ledger in INDEX; assignment permits scoped work, not a phase-exit claim. Recheck dependencies at dispatch; no NORTHSTAR status edits here.
- Existing-tool choice (I-01): Existing SQLite transactions and feed adapter; no new scheduler or database.
- Value/effort estimate: **5/5 value ÷ 2 effort units = 2.50**. Estimates prioritize impact and unblocking, not promised revenue.

## Verification — specified before implementation

Seed good data, inject a >1% count mismatch, missing canary and schema removal, then show each retains the previous queryable snapshot. A valid replacement is promoted atomically.

Run `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/feeds/tests`. Builders first reproduce the defect and have an independent evaluator freeze any missing acceptance case; ordinary unit tests do not substitute for that evaluator. Tester-only cards never repair the product they judge. Follow the launch contract for real-backend proof and final reporting.

Finish with commit hash, changed files, commands/results, fixture versus real evidence, and remaining owner steps. Do not send, publish, sign, file, spend, create accounts, delete owner data or decide legal questions. Use synthetic/local evidence unless an already-authorized read-only source is available.
