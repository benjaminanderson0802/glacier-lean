# Venture test run record — 2026-10-10

Interpreter: `~/w/glacier-lean/.venv/bin/python`. Each venture test directory was run in its own pytest process as requested. `xfailed`/`xpassed` markers are reported as pytest reported them; acceptance checks were not edited.

## Owner guide acceptance

`~/w/glacier-lean/.venv/bin/python -m pytest ventures/tests/acceptance/test_v_ownerguide.py -q --runxfail` — **4 passed**. This includes the two owner-guide regeneration checks, assigned account facts/manual actions, remaining failures with causes, and fixture/live wording.

## Venture directories

| Test directory | Result |
| --- | --- |
| `ventures/apify-tools-louisiana/tests` | 9 passed; 3 live subtests passed |
| `ventures/apify-tools/tests` | 10 passed, 1 skipped, 1 xfailed, 1 xpassed; 3 subtests passed |
| `ventures/blocks/connectors/tests` | 18 passed |
| `ventures/blocks/customer/tests` | 10 passed |
| `ventures/blocks/deadlines/tests` | 6 passed |
| `ventures/blocks/feeds/tests` | 15 passed |
| `ventures/blocks/filer/tests` | 3 failed |
| `ventures/blocks/mail/tests` | 4 passed |
| `ventures/blocks/reader/tests` | 3 passed |
| `ventures/blocks/rules/tests` | 3 passed |
| `ventures/carpenter-goods/tests` | 10 passed, 1 xfailed, 1 xpassed |
| `ventures/coop-postcards/tests` | 11 passed, 2 xfailed |
| `ventures/cpsc-prep/tests` | 19 passed, 1 skipped, 1 xpassed |
| `ventures/dibbs-supply/tests` | 18 passed, 2 xfailed |
| `ventures/fda-cosmetics/tests` | 14 passed, 1 xfailed |
| `ventures/freight-claims/tests` | 34 passed, 1 xfailed |
| `ventures/osha-filing/tests` | 16 passed, 1 xfailed |
| `ventures/property-tax/tests` | 7 passed, 1 xfailed, 1 xpassed |
| `ventures/recall-actor/tests` | 10 passed, 2 skipped, 2 xfailed, 1 xpassed; 3 subtests passed |
| `ventures/recall-checker/tests` | 10 passed, 1 failed |
| `ventures/utility-audits/tests` | 13 passed, 1 xfailed, 1 xpassed |
| `ventures/warranty/tests` | 22 passed, 1 xfailed |
| `ventures/tests` | 18 passed, 3 xpassed |

## Remaining test failures and causes

- `ventures/blocks/filer/tests` — all three browser acceptance checks fail because Node cannot resolve the Playwright package required by `ventures/blocks/filer/runner.mjs` (`MODULE_NOT_FOUND`).
- `ventures/recall-checker/tests/test_recall_checker.py::RecallMatcherAcceptanceTests::test_clean_item_uses_required_source_and_date_vocabulary` — the check expects `no match in …`; the implementation and venture contract require `no match found in …`. The check was left unchanged.

The installer suite now passes in this run (`ventures/tests`: 18 passed, 3 xpassed); its earlier stale two-flow failure is no longer current. A prior combined `pytest ventures` invocation failed during collection because the generic `src` and `scripts` package names collided across venture directories. This card used isolated per-directory runs and did not repeat the combined invocation.

Passing fixture, local, or sandbox checks do not establish live account behavior, customer data processing, filing, publication, or public operation. See [OWNER-START-HERE.md](OWNER-START-HERE.md) and the linked venture `PROOF.md` files for current evidence and launch gates.
