# U-VENTURES verification

This card implements the read-only ventures view and engine-backed “run now” path.

## Checks run

- `cd glacier/backend && /home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q tests/test_venture_summary_unit.py` — 6 passed.
- `cd glacier/web && npx tsc -b` — passed.
- `cd glacier/web && node e2e/theme_lint.mjs` — passed (53 files).
- `cd glacier/web && node scripts/check-i18n.mjs --fail` — passed (965 matching keys/placeholders).
- `cd glacier/web && npm run build` — passed.
- `cd glacier/web && node e2e/venture-summary.spec.mjs` — passed against the mock; the existing preview flow completed.
- `cd glacier/web && node e2e/venture-summary.spec.mjs --live` — passed against a real local backend and installed OSHA flows. The real engine run `a36a983c5348` reached its existing owner approval (`waiting_on: owner_input_ready`). It did not submit anything externally.
- `cd glacier/web && node e2e/ventures.spec.mjs` — fails at its old expected label `setting up`; this card displays the requested `live` / `ready` / `blocked` readiness. That tester-owned check also expects editable setup cards and pause/resume controls, which conflict with this card's read-only direction. The check was not modified.

Playwright screenshots at 1440×900 and 1280×800 for both mock and real backend runs are in `docs/ui/evidence/U-VENTURES/`. The browser check found no horizontal page overflow and no page errors.

## Outstanding verification

The prior worker filed `CLM-2026-10-10-U-VENTURES-VERIFICATION` after a backend suite attempt hit DBOS startup timeout and SQLite lock contention. The focused projection tests and real-backend browser run above pass; the claim remains open for integration/tester review. The full backend suite was not rerun here.

The worktree remains 12 commits behind `origin/glacier-final`. Inspecting the divergence reported two zero-byte Git object files in the shared repository object store (`cf85d3ede3097fc0714fd25e9c38d64f4f07d6bc` and `47c94d4db98e74e874124a5e6c5095b634430ef0`). I did not attempt a rebase against a damaged object store; this is included in the open environment claim for the integrator to resolve.
