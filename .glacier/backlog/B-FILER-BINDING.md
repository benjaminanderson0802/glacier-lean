# B-FILER-BINDING — Bind portal submission to the prepared destination and fields

Owner: Benjamin. Proposed launch card from T-FIND, 2026-10-10. Read [INDEX.md](INDEX.md#launch-contract), AGENTS.md, NORTHSTAR.yaml and ORCHESTRATION.yaml first. Commit on `card/B-FILER-BINDING`; never push.

## Scope

Allowed edits: `ventures/blocks/filer/portal.py; ventures/blocks/filer/runner.mjs`. Also allowed: `evidence/backlog/B-FILER-BINDING/` and a card-specific claim in `vault/claims/`. New ordinary unit tests must live under the affected module’s `tests/unit/` and use this card ID in the filename; no existing test edits. Existing tests, acceptance files and CHECK.md files are read-only. No other paths are authorized.

Exclusive lane: **filer**. Run after B-FILER-SETUP and before B-FILER-RECOVERY in the exclusive filer lane. Backend approval changes, if needed, are an integrator handoff to E-PH3.

## Goal and evidence

prepare validates the starting URL, but submit trusts mutable draft base_url/fields and the browser runner has no explicit request allowlist. Reproduce with local origins before changing.

Bind reviewed fields, destination and customer scope to the cached preparation; reject tampered drafts and unexpected navigation. Reuse existing approval authority through its public contract, never accept a made-up string as new authority.

Read first:

- [ventures/blocks/filer/portal.py](../../ventures/blocks/filer/portal.py) (prepare, submit)
- [ventures/blocks/filer/runner.mjs](../../ventures/blocks/filer/runner.mjs)

## Drift check

- Checkpoint: **PH7.1, PH12.7**. Properties: **P-SECURE, P-CONTROL**. Metrics: **M-SECURITY, M-AUDIT**.
- Dependencies: use the phase ledger in INDEX; assignment permits scoped work, not a phase-exit claim. Recheck dependencies at dispatch; no NORTHSTAR status edits here.
- Existing-tool choice (I-01): Existing Playwright routing and hashing; do not invent a second approval system.
- Value/effort estimate: **5/5 value ÷ 3 effort units = 1.67**. Estimates prioritize impact and unblocking, not promised revenue.

## Verification — specified before implementation

Independent local portals attempt a destination swap, edited fields, cross-origin redirect and replay under another customer. Reject each before external action; retain the normal prepare/review/confirmation path.

Run `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/filer/tests`. Builders first reproduce the defect and have an independent evaluator freeze any missing acceptance case; ordinary unit tests do not substitute for that evaluator. Tester-only cards never repair the product they judge. Follow the launch contract for real-backend proof and final reporting.

Finish with commit hash, changed files, commands/results, fixture versus real evidence, and remaining owner steps. Do not send, publish, sign, file, spend, create accounts, delete owner data or decide legal questions. Use synthetic/local evidence unless an already-authorized read-only source is available.
