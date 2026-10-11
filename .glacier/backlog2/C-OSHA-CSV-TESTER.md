# C-OSHA-CSV-TESTER — Independently verify unsigned OSHA worksheet inputs

Owner: Benjamin. Role: **TESTER only**.

## Scope

Exclusive lane: `osha-worksheet-evaluator`. Allowed edits: new `ventures/osha-filing/tests/acceptance/test_C_worksheet.py` and `evidence/backlog2/C-OSHA-CSV-TESTER/`. No source-feed, eligibility, filing or existing-check edits.

## Goal

Check that a supplied injury-log CSV maps only documented values into an unsigned 300A review worksheet, records source row/date provenance, and leaves missing or inapplicable fields explicit. No test may certify employer eligibility or submit to ITA.

Read first: `ventures/osha-filing/ACCEPTANCE.md`, `PROOF.md`, `README.md`, `ventures/SPEC.md` OSHA section.

## Drift check

- Checkpoint: PH12.16. PH5/PH9 remain in progress; PH12 work is owner-authorized.
- Properties/metrics: P-VERIFY, P-CONTROL; M-VERIFIED, M-AUDIT.
- Existing tools: current CSV parser, rules checker, fixtures and pytest; no filing service.
- Acceptance first: every populated field maps to a supplied row, uncertain facts remain flagged, signature/submission fields remain empty and no external request occurs.

## Verification

Run the new test and `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/osha-filing/tests`. No real injury data or ITA credentials.
