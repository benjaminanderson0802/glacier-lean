# B-SAM-INTEGRITY — Reject misleading comparisons of incomplete SAM snapshots

Owner: Benjamin. Proposed launch card from T-FIND, 2026-10-10. Read [INDEX.md](INDEX.md#launch-contract), AGENTS.md, NORTHSTAR.yaml and ORCHESTRATION.yaml first. Commit on `card/B-SAM-INTEGRITY`; never push.

## Scope

Allowed edits: `ventures/sam-amendment-alerts/scripts/digest.py`. Also allowed: `evidence/backlog/B-SAM-INTEGRITY/` and a card-specific claim in `vault/claims/`. New ordinary unit tests must live under the affected module’s `tests/unit/` and use this card ID in the filename; no existing test edits. Existing tests, acceptance files and CHECK.md files are read-only. No other paths are authorized.

Exclusive lane: **sam-digest**. No active overlap. Can use supplied snapshots independently of B-SAM-COLLECT; integrator agrees additive metadata before those two cards merge.

## Goal and evidence

_records overwrites duplicate notice IDs; build_digest compares snapshots without checking completeness, chronological order or identical collection scope.

Validate comparable snapshot provenance and duplicate conflicts before creating a no-change report. Missing/partial/incompatible evidence must be uncertain; never infer cancellation solely from absence.

Read first:

- [ventures/sam-amendment-alerts/scripts/digest.py](../../ventures/sam-amendment-alerts/scripts/digest.py) (_records, build_digest)

## Drift check

- Checkpoint: **PH12.5**. Properties: **P-VERIFY, P-USABLE**. Metrics: **M-FALSE-DONE, M-VERIFIED**.
- Dependencies: use the phase ledger in INDEX; assignment permits scoped work, not a phase-exit claim. Recheck dependencies at dispatch; no NORTHSTAR status edits here.
- Existing-tool choice (I-01): Existing JSON parser and digest; no new search or alert service.
- Value/effort estimate: **4/5 value ÷ 2 effort units = 2.00**. Estimates prioritize impact and unblocking, not promised revenue.

## Verification — specified before implementation

Independent cases include reversed dates, different NAICS windows, partial pagination, conflicting duplicate IDs and identical complete snapshots. Preserve factual deadline/amendment changes and source links.

Run `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/sam-amendment-alerts/tests`. Builders first reproduce the defect and have an independent evaluator freeze any missing acceptance case; ordinary unit tests do not substitute for that evaluator. Tester-only cards never repair the product they judge. Follow the launch contract for real-backend proof and final reporting.

Finish with commit hash, changed files, commands/results, fixture versus real evidence, and remaining owner steps. Do not send, publish, sign, file, spend, create accounts, delete owner data or decide legal questions. Use synthetic/local evidence unless an already-authorized read-only source is available.
