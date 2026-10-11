# T-APIFY3 acceptance findings

Product code was not edited. The acceptance failures remain visible and no
`xfail` was added.

## Results

- Combined offline acceptance command: `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/apify-census-permits/tests/acceptance ventures/apify-fdic-bankfind/tests/acceptance ventures/apify-npi-batch/tests/acceptance` → **25 passed, 7 failed, 3 skipped** (live tests gated off).
- Combined live command, run once: `RUN_LIVE=1 ~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/apify-census-permits/tests/acceptance ventures/apify-fdic-bankfind/tests/acceptance ventures/apify-npi-batch/tests/acceptance` → **25 passed, 7 failed**; all three live Actor canaries passed. Three additional offline billing assertions were added after that live run and passed in the final offline run.
- The live default-prefill Actor main ran in local SDK mode, made only GET requests to `npiregistry.cms.hhs.gov`, and wrote MAYO CLINIC (NPI 1881018208), including its source-backed primary taxonomy and location. No cloud token, charge, publish, or external write was used.
- Full live row and source hash: [acceptance-live.json](tests/acceptance/evidence/acceptance-live.json).

## Failing acceptance checks

- `test_no_match_is_explicit_and_free` confirms the zero-result API response is `no_match` and `billable=false`, but the message is `No public NPPES record returned for this NPI at retrieval time; not proof of invalid credentials.` It lacks the requested `no match found in NPPES as of [date]` vocabulary and date.
- `test_duplicate_inputs_are_queried_once_and_batch_partial_failure_is_retained`, `test_api_error_count_mismatch_and_identity_mismatch_are_uncertain`, and `test_malformed_source_fails_closed_and_uncertainty_uses_required_vocabulary` confirm outage, malformed, rate-limit/error-envelope, count-mismatch and identity-mismatch rows are `uncertain` and `billable=false`, but their messages only say `...; please check source.` They omit the required literal `uncertain - please check` vocabulary.

These are real output-contract mismatches; the tests remain failing.

## Passing coverage

Tests use the captured CMS v2.1 `result_count` / `results` source shape and
check checksum rejection before traffic, exact identity, duplicate inputs,
partial batch results, Unicode, LOCATION vs MAILING, unique primary taxonomy,
unknown optional fields with warnings, private-field exclusion, bounded HTTP
behavior, success-only charging and the local Actor-main prefill path.
