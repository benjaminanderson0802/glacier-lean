# B-DIBBS-INTAKE implementation evidence

## Drift check

- Checkpoint: PH12.19 (DIBBS venture). This scoped change does not claim a PH12 phase exit.
- Dependencies: PH12 depends on PH5 and PH9, both in progress. The phase ledger in `.glacier/backlog/INDEX.md` explicitly authorizes PH12 scoped parallel work while those dependencies remain in progress.
- Properties and metrics: P-VERIFY / M-VERIFIED for rows backed by independently checkable input digests; P-CONTROL / M-AUDIT for traceable owner confirmation and a still-unsigned, unsubmitted artifact.
- Existing tools: reused the current parser, quote CSV writer, and Python standard-library SHA-256. No DIBBS scraping, new dependency, account, purchase, or submission was added.
- Acceptance first: the independent criteria are frozen in `acceptance.md`; the card-specific unit tests were added and shown failing against the old behavior before the implementation change.

## Reproduction

Before the change, the DIBBS suite reported 20 passed. A synthetic local solicitation and quote with no provenance or owner confirmation nevertheless produced one ranked bid and a CSV; the ranked row had no source hash or acquisition date. The reproduction used no network or real supplier data.

## Verification

- `/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/dibbs-supply/tests/unit/test_B-DIBBS-INTAKE.py` — 8 passed.
- `/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/dibbs-supply/tests` — 26 passed, 2 failed. The failing existing tests are `test_prepares_ranked_batch_with_exact_part_supplier_and_margin` and `test_daily_feed_alert_stays_visible_even_when_a_local_quote_matches`; both expect matches from records without the newly required provenance/confirmation. They are unchanged and read-only under this card. The conflict is filed in `vault/claims/2026-10-11-b-dibbs-intake-legacy-tests.md`.
- Real backend fixture-through-engine: started a disposable FastAPI backend on an ephemeral localhost port with a temporary `GLACIER_HOME`, sent a synthetic confirmed detail/quote through a command node, and independently checked the generated CSV and provenance sidecar. Run `090ad0efbe8e` finished `done`, `verified: true`; CSV and sidecar existed. The backend was started and stopped by this check. No real SAM request, DIBBS page access, supplier contact, or owner data was used.
- `git diff --check` — passed after the final adjustment.

## Anti-pattern review

The change produces working intake validation and trace output. It does not change checkpoint status, broaden the venture scope, or claim real-source proof. The two legacy test failures are reported and claimed rather than hidden or repaired by editing their checks.

## Owner steps still required

For real intake, the owner supplies current DIBBS detail and supplier quote files, acquisition dates, quote revision, and fresh confirmation digests, and separately handles SAM key setup, CAGE/registration, actual supplier quotes, signatures, and submission. This artifact does not establish legal or procurement eligibility.
