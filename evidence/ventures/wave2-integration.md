# I2 wave 2 integration record

Branch: `card/gf-I2`, based on `origin/glacier-final`.

Drift check: advances PH12.22, assigned in ORCHESTRATION wave 6. PH12 depends on PH5 and PH9, which NORTHSTAR currently lists as `in_progress`; the assignment authorizes starting, while their incomplete exits prevent marking this checkpoint done. The work serves P-CONTROL/P-USABLE and M-AUDIT. Acceptance was written as the assigned block release checks, every venture test, full backend pytest, `npm run check:ui`, and real Glacier install/dry-runs with screenshots. Existing OSS blocks and the local Glacier runtime are reused; no new dependency or paid service was added.

## Merges

- `6e05a68` — `card/gf-B1` reader and rules blocks, merged with `--no-ff`. Conflicts resolved in `ventures/SPEC.md`, package initializers, and `ventures/blocks/CONTRACT.md`; retained the canonical SPEC and unioned all eight block contracts and the filing-safety clauses.
- `48fec85` — `card/gf-V-CPSC`, merged with `--no-ff`. `ventures/install_all.py` combines schema/catalog validation with CPSC's workspace script staging and runtime flow preparation.
- `23c57e9` — `card/gf-V-COOP`, merged with `--no-ff`.

Skipped because their final marker files were absent at both checks: `card/gf-P1`, `card/gf-P2`, `card/gf-P3`, `card/gf-V-APIFY`, and `card/gf-V-WARRANTY`.

## Checks completed so far

- `.venv/bin/python ventures/install_all.py --dry-run` — exit 0; all eight manifest flows across carpenter goods, co-op/postcards, and CPSC validated against the schema and node catalog.
- `.venv/bin/python -m py_compile ventures/install_all.py ventures/blocks/reader/reader.py ventures/cpsc-prep/scripts/cpsc_prep.py` — exit 0.
- JSON parse of all venture JSON files found — passed.
- `git diff --check` — passed.
- `heavy .venv/bin/python -m pytest -q ventures` before the reader fix — **79 passed, 2 failed**. One failure was the reader disagreement behavior and is fixed in code; one is the co-op test's stale assumption that the shared rules block is absent. The test was not changed under I-04.
- `heavy .venv/bin/python -m pytest -q ventures/blocks/reader/tests ventures/blocks/rules/tests` after the reader fix — **6 passed**.
- `heavy .venv/bin/python -m pytest -q ventures/blocks/customer/tests` — queued for 2m33s without acquiring a heavy-job slot; canceled at the task's 15-minute shared-environment backstop. This is covered by the existing `claim-ph12-22-heavy-test-lock` environment claim.

## Still pending

Remaining block release checks, feed sync/repeat run, full backend pytest, `npm run check:ui`, `npm run live`, fresh installer registration, real Glacier dry-runs, and screenshots were not run because the shared heavy-job slots remained occupied beyond the worker backstop. No release checkpoint is claimed complete in this record.
