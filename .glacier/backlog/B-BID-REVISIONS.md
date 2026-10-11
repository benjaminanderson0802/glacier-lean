# B-BID-REVISIONS — Keep later supplied bid notices from being silently discarded

Owner: Benjamin. Proposed launch card from T-FIND, 2026-10-10. Read [INDEX.md](INDEX.md#launch-contract), AGENTS.md, NORTHSTAR.yaml and ORCHESTRATION.yaml first. Commit on `card/B-BID-REVISIONS`; never push.

## Scope

Allowed edits: `ventures/al-bid-triage/scripts/bid_triage.py`. Also allowed: `evidence/backlog/B-BID-REVISIONS/` and a card-specific claim in `vault/claims/`. New ordinary unit tests must live under the affected module’s `tests/unit/` and use this card ID in the filename; no existing test edits. Existing tests, acceptance files and CHECK.md files are read-only. No other paths are authorized.

Exclusive lane: **al-bid**. Only parser code; A-CASH owns offers, README/PILOT/prospects and V-AUTOMATE owns the flow.

## Goal and evidence

build_digest deduplicates by notice_number before filtering, keeping the first row regardless of issuer or received_at. A later amendment can disappear.

Use issuer-aware identity and supplied provenance to retain the latest unambiguous notice; surface conflicting revisions as uncertain. Keep earlier/new dates visible without asserting the legal controlling deadline.

Read first:

- [ventures/al-bid-triage/scripts/bid_triage.py](../../ventures/al-bid-triage/scripts/bid_triage.py) (build_digest)
- [ventures/research/R-LOCAL.md](../../ventures/research/R-LOCAL.md)

## Drift check

- Checkpoint: **PH12.5**. Properties: **P-VERIFY, P-USABLE**. Metrics: **M-VERIFIED, M-INTERVENE**.
- Dependencies: use the phase ledger in INDEX; assignment permits scoped work, not a phase-exit claim. Recheck dependencies at dispatch; no NORTHSTAR status edits here.
- Existing-tool choice (I-01): Existing CSV/datetime pipeline; no crawling or paid bid feed.
- Value/effort estimate: **4/5 value ÷ 2 effort units = 2.00**. Estimates prioritize impact and unblocking, not promised revenue.

## Verification — specified before implementation

Independent fixtures reverse input order, reuse a number across issuers, and change county/deadline in an amendment. The digest remains deterministic and links every retained revision to supplied source evidence.

Run `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/al-bid-triage/tests`. Builders first reproduce the defect and have an independent evaluator freeze any missing acceptance case; ordinary unit tests do not substitute for that evaluator. Tester-only cards never repair the product they judge. Follow the launch contract for real-backend proof and final reporting.

Finish with commit hash, changed files, commands/results, fixture versus real evidence, and remaining owner steps. Do not send, publish, sign, file, spend, create accounts, delete owner data or decide legal questions. Use synthetic/local evidence unless an already-authorized read-only source is available.
