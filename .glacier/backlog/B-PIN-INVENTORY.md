# B-PIN-INVENTORY — Make the existing health report account for venture dependency pins

Owner: Benjamin. Proposed launch card from T-FIND, 2026-10-10. Read [INDEX.md](INDEX.md#launch-contract), AGENTS.md, NORTHSTAR.yaml and ORCHESTRATION.yaml first. Commit on `card/B-PIN-INVENTORY`; never push.

## Scope

Allowed edits: `setup/health_check.py; new setup/dependency_inventory.py`. Also allowed: `evidence/backlog/B-PIN-INVENTORY/` and a card-specific claim in `vault/claims/`. New ordinary unit tests must live under the affected module’s `tests/unit/` and use this card ID in the filename; no existing test edits. Existing tests, acceptance files and CHECK.md files are read-only. No other paths are authorized.

Exclusive lane: **health**. Serialize after B-HEALTH-VENTURES because both edit health_check.py. Keep E-PH8 packaging and A-CASH Actor materials read-only.

## Goal and evidence

The current upgrade inventory only reads exact pins in setup/requirements.txt; separately packaged venture dependencies are outside that inventory.

Extend read-only inventory to existing venture manifests/locks, reporting unpinned entries, provenance and the owning path. Produce proposals only; do not alter dependencies, licenses or active Actor packages.

Read first:

- [setup/health_check.py](../../setup/health_check.py) (pinned_requirements)
- [setup/requirements.txt](../../setup/requirements.txt)
- `ventures/*/requirements.txt`
- `ventures/*/package-lock.json`

## Drift check

- Checkpoint: **PH11.1**. Properties: **P-PORTABLE, P-SECURE**. Metrics: **M-SURVIVE, M-SECURITY**.
- Dependencies: use the phase ledger in INDEX; assignment permits scoped work, not a phase-exit claim. Recheck dependencies at dispatch; no NORTHSTAR status edits here.
- Existing-tool choice (I-01): Existing pip/npm manifest formats and health report; no SBOM platform or new dependency resolver.
- Value/effort estimate: **3/5 value ÷ 2 effort units = 1.50**. Estimates prioritize impact and unblocking, not promised revenue.

## Verification — specified before implementation

Independent temporary manifests include exact pins, ranges, transitive locks and missing files; report each accurately without installing or upgrading. Verify existing health tests still pass and scan actual repository manifests.

Run `~/w/glacier-lean/.venv/bin/python -m pytest -q setup/test_health_check.py`. Builders first reproduce the defect and have an independent evaluator freeze any missing acceptance case; ordinary unit tests do not substitute for that evaluator. Tester-only cards never repair the product they judge. Follow the launch contract for real-backend proof and final reporting.

Finish with commit hash, changed files, commands/results, fixture versus real evidence, and remaining owner steps. Do not send, publish, sign, file, spend, create accounts, delete owner data or decide legal questions. Use synthetic/local evidence unless an already-authorized read-only source is available.
