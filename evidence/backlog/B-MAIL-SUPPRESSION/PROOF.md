# B-MAIL-SUPPRESSION proof

## Drift check and acceptance

- Checkpoint: PH12.7. The PH12 dependencies PH5 and PH9 remain in progress; this assigned card advances scoped work only and makes no phase-exit claim.
- Property and metrics: P-CONTROL; M-AUDIT and M-INTERVENE.
- Existing tool / I-01: reuse the mail block's local plain-text suppression list and address adapter. No new dependency or external normalizer was needed.
- Acceptance: equivalent case, punctuation, whitespace, common address-field/street/unit aliases, and ZIP5/ZIP+4 spellings remain suppressed; different unit numbers remain distinct; the file stays readable UTF-8 text; a later attempt sees a new opt-out; a suppressed postcard makes no postal transport request.

The independent evaluator froze [independent_acceptance.py](independent_acceptance.py) before the product edit. Its baseline was **2 failed, 5 passed**: punctuation/field aliases and ZIP5/ZIP+4 did not match. After implementation it reports **7 passed**.

## Verification

- `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/mail/tests` — **17 passed**.
- `~/w/glacier-lean/.venv/bin/python -m pytest -q evidence/backlog/B-MAIL-SUPPRESSION/independent_acceptance.py ventures/blocks/mail/tests/unit/test_B-MAIL-SUPPRESSION.py` — **11 passed**.
- `py_compile` for the engine and new unit test, plus `git diff --check` — passed.
- A real Glacier backend started with disposable `GLACIER_HOME=/tmp/glacier-mail-suppression-real-backend` on `127.0.0.1:18765`; `GET /api/health` returned HTTP 200. The engine then wrote a synthetic suppression entry in that home; an equivalent same-unit attempt failed and Apartment 3 passed. The backend was stopped cleanly. No Lob or other postal request was made.

The backend health/startup is real local backend evidence. Address matching, durability and no-request results are synthetic fixture-through-engine evidence; there is no customer, Lob test-account, or production mailing evidence.
