# B-SAM-COLLECT — Collect bounded SAM snapshots for the existing pilot

Owner: Benjamin. Proposed launch card from T-FIND, 2026-10-10. Read [INDEX.md](INDEX.md#launch-contract), AGENTS.md, NORTHSTAR.yaml and ORCHESTRATION.yaml first. Commit on `card/B-SAM-COLLECT`; never push.

## Scope

Allowed edits: `new ventures/sam-amendment-alerts/scripts/collect_snapshot.py; new ventures/sam-amendment-alerts/SOURCE-SETUP.md`. Also allowed: `evidence/backlog/B-SAM-COLLECT/` and a card-specific claim in `vault/claims/`. New ordinary unit tests must live under the affected module’s `tests/unit/` and use this card ID in the filename; no existing test edits. Existing tests, acceptance files and CHECK.md files are read-only. No other paths are authorized.

Exclusive lane: **sam-collector**. A-CASH owns README/PILOT/prospects and sales strategy; V-AUTOMATE owns flows. This card only adds source intake code and its separate setup note.

## Goal and evidence

The pilot compares saved snapshots only; A-CASH identifies current snapshot collection as a remaining fulfillment gate.

Reuse the existing DIBBS official-API request approach, read-only, to collect selected NAICS notices with complete pagination, retrieval date, query scope and source URL. Store keys only in Glacier Secrets; save no partial snapshot as complete.

Read first:

- [ventures/sam-amendment-alerts/scripts/digest.py](../../ventures/sam-amendment-alerts/scripts/digest.py)
- [ventures/sam-amendment-alerts/README.md](../../ventures/sam-amendment-alerts/README.md)
- [ventures/research/R-GOVDATA.md](../../ventures/research/R-GOVDATA.md)
- [ventures/dibbs-supply/scripts/dibbs_supply.py](../../ventures/dibbs-supply/scripts/dibbs_supply.py)

## Drift check

- Checkpoint: **PH12.5**. Properties: **P-LOOPS, P-USABLE**. Metrics: **M-INTERVENE, M-VERIFIED**.
- Dependencies: use the phase ledger in INDEX; assignment permits scoped work, not a phase-exit claim. Recheck dependencies at dispatch; no NORTHSTAR status edits here.
- Existing-tool choice (I-01): Existing httpx/urllib, keychain and DIBBS request logic; official API only, no SAM scraping.
- Value/effort estimate: **5/5 value ÷ 3 effort units = 1.67**. Estimates prioritize impact and unblocking, not promised revenue.

## Verification — specified before implementation

Fixture transport exercises multi-page results, quota errors and truncation. Run a bounded real read only if the owner-configured free key is available; otherwise report that live proof remains pending and demonstrate useful missing-key guidance.

Run `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/sam-amendment-alerts/tests`. Builders first reproduce the defect and have an independent evaluator freeze any missing acceptance case; ordinary unit tests do not substitute for that evaluator. Tester-only cards never repair the product they judge. Follow the launch contract for real-backend proof and final reporting.

Finish with commit hash, changed files, commands/results, fixture versus real evidence, and remaining owner steps. Do not send, publish, sign, file, spend, create accounts, delete owner data or decide legal questions. Use synthetic/local evidence unless an already-authorized read-only source is available.
