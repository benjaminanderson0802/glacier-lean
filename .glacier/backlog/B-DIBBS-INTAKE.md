# B-DIBBS-INTAKE — Trace bid-sheet inputs back to owner-verified solicitation records

Owner: Benjamin. Proposed launch card from T-FIND, 2026-10-10. Read [INDEX.md](INDEX.md#launch-contract), AGENTS.md, NORTHSTAR.yaml and ORCHESTRATION.yaml first. Commit on `card/B-DIBBS-INTAKE`; never push.

## Scope

Allowed edits: `ventures/dibbs-supply/scripts/dibbs_supply.py; new ventures/dibbs-supply/INTAKE-PROVENANCE.md`. Also allowed: `evidence/backlog/B-DIBBS-INTAKE/` and a card-specific claim in `vault/claims/`. New ordinary unit tests must live under the affected module’s `tests/unit/` and use this card ID in the filename; no existing test edits. Existing tests, acceptance files and CHECK.md files are read-only. No other paths are authorized.

Exclusive lane: **dibbs**. Only venture source code. SAM key setup, CAGE/registration, actual quotes and signature remain owner steps; V-AUTOMATE owns flows.

## Goal and evidence

Current real-engine proof exercises the missing-key path; usable bid sheets depend on owner-supplied exact DIBBS details and actual supplier quotes.

Reproduce whether intake binds each ranked row to immutable source hashes, acquisition dates and owner-confirmed detail/quote records. Add missing provenance and reject mismatched or superseded inputs without deciding procurement eligibility.

Read first:

- [ventures/dibbs-supply/PROOF.md](../../ventures/dibbs-supply/PROOF.md)
- [ventures/dibbs-supply/scripts/dibbs_supply.py](../../ventures/dibbs-supply/scripts/dibbs_supply.py)
- [vault/claims/2026-10-10-b2-dibbs-public-feed.md](../../vault/claims/2026-10-10-b2-dibbs-public-feed.md)

## Drift check

- Checkpoint: **PH12.19**. Properties: **P-VERIFY, P-CONTROL**. Metrics: **M-VERIFIED, M-AUDIT**.
- Dependencies: use the phase ledger in INDEX; assignment permits scoped work, not a phase-exit claim. Recheck dependencies at dispatch; no NORTHSTAR status edits here.
- Existing-tool choice (I-01): Existing parser, quote-sheet generator and SHA-256; no DIBBS scraping, account creation, purchases or bid submission.
- Value/effort estimate: **3/5 value ÷ 2 effort units = 1.50**. Estimates prioritize impact and unblocking, not promised revenue.

## Verification — specified before implementation

Independent synthetic records with changed part, quantity, supplier and quote revision cannot silently reuse prior confirmation; complete matching records generate an unsigned CSV with traceable inputs. Real records remain a separate owner-dependent proof.

Run `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/dibbs-supply/tests`. Builders first reproduce the defect and have an independent evaluator freeze any missing acceptance case; ordinary unit tests do not substitute for that evaluator. Tester-only cards never repair the product they judge. Follow the launch contract for real-backend proof and final reporting.

Finish with commit hash, changed files, commands/results, fixture versus real evidence, and remaining owner steps. Do not send, publish, sign, file, spend, create accounts, delete owner data or decide legal questions. Use synthetic/local evidence unless an already-authorized read-only source is available.
