# Independent contractor Actor verification

Checkpoint: PH12.10. Drift check: PH12.10 is in progress; PH5 and PH9 are not at exit, but the owner explicitly authorized parallel PH12 work on 2026-10-10. This card serves P-VERIFY and P-CONTROL, with M-VERIFIED and M-AUDIT. Existing tools used: the local Apify SDK, pytest, and the Actors' captured canary/source fixtures. Acceptance checks were written before the suite runs. No cloud Actor, live billing, upload, price change, or publication was used.

## Commands and results

- `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/apify-tools/tests`: **1 failed, 17 passed, 1 skipped, 3 canary subtests passed**. Log: `mississippi-pytest.log`.
- `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/apify-tools-louisiana/tests`: **1 failed, 14 passed, 3 live canary subtests passed**. Log: `louisiana-pytest.log`.

Both suite failures are the new independent test `test_uncertain_or_unverifiable_lookup_does_not_emit_billable_event[uncertain]`. The runner emits a `license-lookup` charge for an uncertain detail result. Verified matches and dated verified no-match results charge once when the local test billing switch is enabled; `unverifiable` source outages do not charge. Without the local test opt-in, a verified result does not charge. See claim `CLM-2026-10-11-C-APIFY-MS-LA-UNCERTAIN-BILLING`.

## Other acceptance checks

- The suite live canaries rechecked the three stored known records for each state, with matching names/statuses/expirations and UTC check timestamps; the Louisiana test also verifies direct official detail URLs. Mississippi's live-name lookup and both boards' rate-limit, no-match, and outage cases passed.
- Existing stale-canary tests passed: a changed/unverifiable canary sets maintenance state without an automatic repair attempt.
- New checks confirmed each Actor dataset schema declares its overview output columns.
- Fresh local Apify SDK entrypoint runs completed with exit code 0 for both packages using temporary local storage, `APIFY_IS_AT_HOME` unset, and `ACTOR_TEST_PAY_PER_EVENT` unset. Mississippi emitted a verified match for `22649`; Louisiana emitted a verified match for `CL.68755`. Output rows are saved in `mississippi-local-sdk-output.json` and `louisiana-local-sdk-output.json`.

No NORTHSTAR checkpoint status was changed: PH12.10 remains in progress, and a billing-boundary claim is open.
