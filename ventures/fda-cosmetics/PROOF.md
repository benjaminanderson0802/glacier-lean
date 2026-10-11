# Proof — FDA cosmetics listing preparation

## Acceptance checks

- `~/w/glacier-lean/.venv/bin/python -m pytest ventures/fda-cosmetics/tests/acceptance/test_v_fda2.py::test_shopify_graphql_fixture_produces_field_sources_and_uncertainty -q --runxfail` — **1 failed before venture code ran**. The acceptance fixture cannot be decoded as JSON (`JSONDecodeError` at line 2, column 1, character 477); details and a corrected-check request are in [DISPUTE.md](DISPUTE.md). The protected acceptance files were not modified.

- Adapter smoke check — **passed** using the fixture content with its missing outer `}` supplied in memory (no acceptance file changed). `prepare_from_shopify` returned a review-ready response with sourced fields, explicit uncertainty for catalog-only or brand-confirmed facts, and `filing_ready: false`, `submitted: false`.

- `~/w/glacier-lean/.venv/bin/python -m pytest ventures/fda-cosmetics -q` — **14 passed, 1 xfailed**. Existing venture tests use a fixture shaped like Shopify GraphQL `data.products.edges[].node`, run it through `ShopifyClient.get_products`, and check packet provenance, uncertainty flags, missing label-name handling, ingredient checklist, 120-day/annual reminder dates, and the read-only owner check contract. The xfailed independent fixture check is documented above.
- `~/w/glacier-lean/.venv/bin/python ventures/install_all.py --only fda-cosmetics --dry-run` — **both flows validated** (`prepare-listing-packet`, `daily-deadline-reminders`).
- The read-only owner script invokes only `ShopifyClient.test_connection()` and `get_products()`. Its test uses a stubbed client; it was **not run against a live store** in this worktree.

The listing packet emits a value, source, confidence, page when available, and `uncertain` flag for every field. Shopify's catalog title is kept as a separate uncertain cross-reference and is not treated as the product name on the label. Brand confirmation, facility identity/exemption, product category, responsible-person details, ingredient order, and exemption checklist entries remain uncertain when missing or not confirmed. The packet is not generated until its required review fields are complete. The customer remains the only signer and submitter.

The earlier recorded synthetic SPL XSD check was not repeated in this update. A fixture-generated SPL ZIP is exercised by the focused suite, but no live Shopify catalog, brand label, Cosmetics Direct response, or FDA filing was available. Cosmetics Direct performs its own technical and business validation, so a local packet is not evidence of FDA acceptance. Automated 30-day retention deletion and customer-layer billing remain launch dependencies.

## Other venture-suite status

Individual suites run from their venture directories passed for Apify tools, Shopify/Jobber/ShipStation connectors, customer, deadlines, feeds, mail, reader, rules, Carpenter's goods, co-op, CPSC, DIBBS, freight, OSHA, property tax, Recall Actor, utility audits, and warranty. The following pre-existing issues remain outside this FDA card:

- `ventures/blocks/filer/tests`: three tests could not start because `ventures/blocks/filer/runner.mjs` cannot resolve the Playwright package under `glacier/web/node_modules/playwright` in this checkout.
- `ventures/recall-checker/tests`: 10 passed and 1 failed because the test expects `no match in ...` while the current global output vocabulary and implementation use `no match found in ...`; see `vault/claims/2026-10-10-ph12-12-recall-output-vocabulary.md`.
- `ventures/tests`: 15 passed and 1 failed because an installer test assumes all discovered flows are Apify flows (`36 != 2`).
- A single `pytest ventures -q` collection also fails before running all tests because `recall-actor` and `utility-audits` import their local `src`/`scripts` packages as top-level modules. Their suites pass when run individually from their venture directories.

No NORTHSTAR checkpoint status was changed. PH12.15 remains in progress pending shared-phase dependencies and live owner-side verification.

## FDA references

- [Form FDA 5067](https://www.fda.gov/cosmetics/registration-listing-cosmetic-product-facilities-and-products/form-fda-5067-cosmetic-product-listing)
- [FDA Direct User's Guide — February 2026](https://www.fda.gov/media/191059/download)
- [Cosmetics Direct](https://direct.fda.gov/)
- [SPL Implementation Guide with Validation Procedures](https://www.fda.gov/media/84201/download)
- [FDA SPL schema and resources](https://www.fda.gov/industry/fda-data-standards-advisory-board/structured-product-labeling-resources)
