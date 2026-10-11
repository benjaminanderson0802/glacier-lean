# Venture test run record — 2026-10-10

Interpreter: `/home/glacier/w/glacier-lean/.venv/bin/python`.

## Root invocation

`~/w/glacier-lean/.venv/bin/python -m pytest -q ventures` — **collection failed** with 3 import errors before the test board ran:

- `ventures/recall-actor/tests/test_live_canary.py` — `src.sources` could not be imported during combined collection; generic `src` package names collide across venture directories.
- `ventures/recall-actor/tests/test_nested_cpsc_fixture.py` — same combined-collection `src.sources` import collision.
- `ventures/utility-audits/tests/test_utility_audit.py` — `scripts.utility_audit` could not be imported during combined collection; generic `scripts` package names collide across venture directories.

Each test directory was therefore run in a separate pytest process. Results:

| Test directory | Result |
| --- | --- |
| `ventures/apify-tools/tests` | 10 passed; 3 subtests passed |
| `ventures/blocks/connectors/tests` | 17 passed |
| `ventures/blocks/customer/tests` | 10 passed |
| `ventures/blocks/deadlines/tests` | 6 passed |
| `ventures/blocks/feeds/tests` | 15 passed |
| `ventures/blocks/filer/tests` | 3 failed |
| `ventures/blocks/mail/tests` | 4 passed |
| `ventures/blocks/reader/tests` | 3 passed |
| `ventures/blocks/rules/tests` | 3 passed |
| `ventures/carpenter-goods/tests` | 6 passed |
| `ventures/coop-postcards/tests` | 9 passed |
| `ventures/cpsc-prep/tests` | 18 passed |
| `ventures/dibbs-supply/tests` | 11 passed |
| `ventures/fda-cosmetics/tests` | 9 passed |
| `ventures/freight-claims/tests` | 23 passed |
| `ventures/osha-filing/tests` | 8 passed |
| `ventures/property-tax/tests` | 6 passed |
| `ventures/recall-actor/tests` | 10 passed, 1 skipped; 3 subtests passed |
| `ventures/recall-checker/tests` | 10 passed, 1 failed |
| `ventures/tests` | 15 passed, 1 failed |
| `ventures/utility-audits/tests` | 9 passed |
| `ventures/warranty/tests` | 17 passed |

## Remaining failures

- `ventures/blocks/filer/tests`: 3 acceptance tests fail because Node cannot resolve the missing Playwright package required by `ventures/blocks/filer/runner.mjs` (`MODULE_NOT_FOUND`).
- `ventures/recall-checker/tests/test_recall_checker.py::test_clean_item_uses_required_source_and_date_vocabulary`: expected wording omits “found”; implementation follows the venture-wide required phrase “no match found in …”. The test was left unchanged.
- `ventures/tests/test_install_all.py::test_discovery_is_data_driven_and_only_filters_by_slug`: stale assertion expects total flow count to equal the two Apify flows, but discovery finds 36 flows across all installed ventures. The test was left unchanged.

These are test results only. Venture launch status is separately gated by the live/source/account conditions in [OWNER-START-HERE.md](OWNER-START-HERE.md).
