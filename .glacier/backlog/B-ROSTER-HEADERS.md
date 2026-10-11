# B-ROSTER-HEADERS — Make roster field mapping deterministic when columns conflict

Owner: Benjamin. Proposed launch card from T-FIND, 2026-10-10. Read [INDEX.md](INDEX.md#launch-contract), AGENTS.md, NORTHSTAR.yaml and ORCHESTRATION.yaml first. Commit on `card/B-ROSTER-HEADERS`; never push.

## Scope

Allowed edits: `ventures/al-license-verify/scripts/verify.py`. Also allowed: `evidence/backlog/B-ROSTER-HEADERS/` and a card-specific claim in `vault/claims/`. New ordinary unit tests must live under the affected module’s `tests/unit/` and use this card ID in the filename; no existing test edits. Existing tests, acceptance files and CHECK.md files are read-only. No other paths are authorized.

Exclusive lane: **al-roster**. Only source parser code; A-CASH owns Actor listing READMEs, price materials and prospects. Source permission remains an owner gate.

## Goal and evidence

Header selection uses next over alias sets, so a CSV containing conflicting synonymous columns can select different values across hash seeds.

Apply documented deterministic aliases and flag conflicting nonblank columns instead of silently selecting a status, expiry or license number. Keep original field provenance for review.

Read first:

- [ventures/al-license-verify/scripts/verify.py](../../ventures/al-license-verify/scripts/verify.py) (HEADER_ALIASES, load_roster_text)

## Drift check

- Checkpoint: **PH12.10**. Properties: **P-VERIFY**. Metrics: **M-FALSE-DONE, M-VERIFIED**.
- Dependencies: use the phase ledger in INDEX; assignment permits scoped work, not a phase-exit claim. Recheck dependencies at dispatch; no NORTHSTAR status edits here.
- Existing-tool choice (I-01): Existing CSV parsing and validation; no new registry, API or commercial service.
- Value/effort estimate: **4/5 value ÷ 2 effort units = 2.00**. Estimates prioritize impact and unblocking, not promised revenue.

## Verification — specified before implementation

Independent fixtures contain license/license_number and status/license_status conflicts; repeated processes with different PYTHONHASHSEED values produce the same uncertainty and no fabricated authoritative value.

Run `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/al-license-verify/tests`. Builders first reproduce the defect and have an independent evaluator freeze any missing acceptance case; ordinary unit tests do not substitute for that evaluator. Tester-only cards never repair the product they judge. Follow the launch contract for real-backend proof and final reporting.

Finish with commit hash, changed files, commands/results, fixture versus real evidence, and remaining owner steps. Do not send, publish, sign, file, spend, create accounts, delete owner data or decide legal questions. Use synthetic/local evidence unless an already-authorized read-only source is available.
