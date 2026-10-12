# T-APIFY3 acceptance findings

Product code was not edited. The acceptance failures remain visible and no
`xfail` was added.

## Results

- Combined offline acceptance command: `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/apify-census-permits/tests/acceptance ventures/apify-fdic-bankfind/tests/acceptance ventures/apify-npi-batch/tests/acceptance` → **25 passed, 7 failed, 3 skipped** (live tests gated off).
- Combined live command, run once: `RUN_LIVE=1 ~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/apify-census-permits/tests/acceptance ventures/apify-fdic-bankfind/tests/acceptance ventures/apify-npi-batch/tests/acceptance` → **25 passed, 7 failed**; all three live Actor canaries passed. Three additional offline billing assertions were added after that live run and passed in the final offline run.
- The live default-prefill Actor main ran in local SDK mode, made only GET requests to `api.fdic.gov`, and wrote Bank of America, National Association (certificate 3510), from the official FDIC institution snapshot. No cloud token, charge, publish, or external write was used.
- Full live row and source hash: [acceptance-live.json](tests/acceptance/evidence/acceptance-live.json).

## Failing acceptance checks

- `test_explicit_empty_result_is_free_no_match` confirms a documented zero-result snapshot is `no_match` and `billable=false`, but its message is `No institution matched these filters in this source snapshot.` It lacks the requested `no match found in FDIC as of [date]` vocabulary and date.
- `test_malformed_or_changed_source_is_uncertain_not_empty` confirms source outage results are `uncertain` and `billable=false`, but the message says `...; retry later.` It omits the required literal `uncertain - please check` vocabulary.

Both are real customer output-contract mismatches; both checks remain failing.

## Passing coverage

Tests use the captured FDIC `meta` / nested `data[].data` institution response;
they verify certificate identity, literal ACTIVE, source vintage, filter and
pagination behavior, Unicode, null optional fields, deduplication, malformed
and partial-page failure, bounded HTTP behavior, no charge for no-match or
outage-only results, write-before-charge, limits and local-mode prefill through
the real Actor main and Apify SDK.
