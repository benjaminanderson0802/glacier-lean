# T-APIFY3 acceptance findings

Product code was not edited. The acceptance tests remain independent and the
customer vocabulary check is intentionally still failing; no `xfail` was added.

## Results

- Combined offline acceptance command: `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/apify-census-permits/tests/acceptance ventures/apify-fdic-bankfind/tests/acceptance ventures/apify-npi-batch/tests/acceptance` → **25 passed, 7 failed, 3 skipped** (live tests gated off).
- Combined live command, run once: `RUN_LIVE=1 ~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/apify-census-permits/tests/acceptance ventures/apify-fdic-bankfind/tests/acceptance ventures/apify-npi-batch/tests/acceptance` → **25 passed, 7 failed**; all three live Actor canaries passed. Three additional offline billing assertions were added after that live run and passed in the final offline run.
- The live default-prefill Actor main ran in local SDK mode, made only GET requests to `www2.census.gov`, wrote local dataset rows for Alabama (01), Louisiana (22), and Mississippi (28), comparing 2026-08 with 2026-07. No cloud token, charge, publish, or external write was used.
- Full live rows and source hashes: [acceptance-live.json](tests/acceptance/evidence/acceptance-live.json).

## Failing acceptance check

`test_source_outage_is_uncertain_and_says_uncertain_please_check` confirms the
row is `outcome=uncertain` and `billable=false`, but the customer message is
`Census release unavailable or unexpected response (...); please check source.`
It omits the required literal `uncertain - please check` vocabulary. This is a
real output-contract mismatch; the test remains failing.

## Passing coverage

The captured official 29-column source files preserve FIPS strings and Unicode,
convert valuation from thousands to dollars, distinguish imputed and reported
units, fail closed on malformed, duplicate, incomplete, wrong-period, missing
state or missing numeric data, enforce bounded HTTP retry/size/timeout behavior,
and exercise success-only charging, write-before-charge and charge limits.
The schema prefill runs through `python -m src` and the real local Apify SDK.
