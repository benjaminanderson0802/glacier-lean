# Proof — FDA cosmetics listing preparation

## Current state

Release remains **blocked**. Both venture flows were installed into a disposable `GLACIER_HOME` and executed through the real local Glacier backend with the valid Shopify GraphQL fixture. The runs reached their owner review steps, where they were intentionally left waiting. No real Shopify store, customer label, FDA account, signature, filing, or external write was used.

The packet flow read one synthetic fixture product and returned `uncertain — please check` because brand-confirmed product details were deliberately absent. It produced no SPL ZIP and reported `submitted: false`. The deadline flow read one synthetic 120-day reminder dated 2026-10-10 and wrote its JSON output. Exact run records and outputs are in [fixture-engine-runs.json](evidence/fixture-engine-runs.json); the local backend install/run request log is in [fixture-engine-run-log.txt](evidence/fixture-engine-run-log.txt).

## Checks run

- `~/w/glacier-lean/.venv/bin/python -m pytest ventures/fda-cosmetics -q` — **17 passed**.
- `~/w/glacier-lean/.venv/bin/python -m pytest ventures/fda-cosmetics/tests/acceptance/test_v_fda2.py -q --runxfail` — **3 passed**. The protected fixture is valid JSON in the current tree; the previously recorded parse failure no longer reproduces. No acceptance file was changed.
- `~/w/glacier-lean/.venv/bin/python -m pytest ventures/blocks/reader/tests/test_acceptance.py -q` — **3 passed**. The previously recorded reader disagreement no longer reproduces. The existing claims remain assigned to their recorded owners and were not edited by this card.
- `~/w/glacier-lean/.venv/bin/python -m pytest ventures/tests -q` — **21 passed**.
- `~/w/glacier-lean/.venv/bin/python ventures/install_all.py --only fda-cosmetics --dry-run` — **both flows validated**.
- Real local backend: `ventures/install_all.py --only fda-cosmetics` installed `prepare-listing-packet` and `daily-deadline-reminders`; run IDs `27d795c6047b` and `532dc5195d17` reached `customer_submit` and `review_reminder` respectively. Both command nodes and the branch checks completed. They remain waiting on owner approval, so the engine reports `verified: null` for both runs.
- `GLACIER_READER_MODEL_TIMEOUT=30 ~/w/glacier-lean/.venv/bin/python -m ventures.blocks.reader.benchmark ventures/blocks/reader/samples/manifest.json` — **100% agreement (7/7 known-value fields)** across the official public sample set. Its FDA cosmetics sample is the FDA Cosmetic Labeling Guide; the `example_ingredient` field matched `castor oil` on page 21. The captured result is [reader-public-benchmark.json](evidence/reader-public-benchmark.json). This is a small extraction benchmark and does not substitute for product-label review.

## Release gates still open

- Automatic 30-day retention deletion and customer-layer billing are not connected. These are non-owner launch dependencies in the shared customer layer and remain outside this venture card.
- The FDA fixture claim `CLM-2026-10-10-PH12-15-LABEL-TEST-FIXTURE` is resolved with the current passing protected acceptance check as evidence. The shared-reader claim `CLM-2026-10-10-PH12-15-READER-CONFLICT-CONTRACT` remains filed and assigned to B1, although its current check passes; that owner needs to reconcile the claim with this evidence. This card did not change another worker's claim.
- The owner must connect Shopify and provide each product's exact current label, ingredient order, category, responsible person, facility/FEI or confirmed exemption, dates, and exemption answers. The responsible person reviews and signs where required, submits through Cosmetics Direct, and forwards the response. Glacier does not perform those steps.
- Shopify App Store review is needed only if the owner chooses public Shopify App Store distribution. It is not needed for local Glacier runs.

Official references were checked against FDA and Shopify pages. The README now links the February 2026 Cosmetics Direct guide at `https://www.fda.gov/media/191059/download`; the FDA SPL implementation guide link at `https://www.fda.gov/media/84201/download` is official and its chapter 3.4 covers cosmetic product data. The earlier APEX guide URL was replaced.

## Evidence limits

The engine run used `ventures/fda-cosmetics/fixtures/shopify-products.graphql.json` through a temporary, local-only fixture adapter. The synthetic deadline row was seeded in the disposable home. This proves installed flow execution, output creation, branching, and owner handoff; it is not a live Shopify run or evidence that a real cosmetic product is compliant or FDA-accepted. A parsed FDA response would also not independently establish acceptance.
