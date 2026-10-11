# C-COOP-FAIL-CLOSED-TESTER evidence

Checkpoint: PH12.13. PH5 and PH9 remain in progress; this independent test does not mark PH12.13 complete or certify a claim for filing.

Drift check: serves P-VERIFY and P-CONTROL, with M-VERIFIED and M-AUDIT. Existing workflow, renderer, and local fixtures cover generation; this card adds only independent test coverage. Acceptance is that missing ad proof, payment evidence, or current program terms leaves a complete local Markdown/PDF/JSON review packet with retained job/source links, explicit gaps, `filing_ready: false`, and no external action.

The new test runs the local fixture CLI against three independently incomplete packets. It checks the Jobber job number and source URL across all formats, unverified program source/terms, absent evidence markers or deadline confirmation, false readiness, and no network/external action. It does not file, send, order, or publish anything.

## Verification

- `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/coop-postcards/tests/acceptance/test_C_coop_release.py` — 3 passed.
- `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/coop-postcards/tests` — 19 passed; full output: `coop-postcards-tests.log`.

Anti-pattern review: the work is an executable independent test, does not rewrite or weaken the disputed check, and makes no checkpoint completion claim. No anti-pattern found.
