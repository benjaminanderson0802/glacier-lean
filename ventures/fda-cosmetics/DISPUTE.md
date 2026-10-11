# Acceptance dispute — V-FDA2 Shopify fixture

## Check

`ventures/fda-cosmetics/tests/acceptance/test_v_fda2.py::test_shopify_graphql_fixture_produces_field_sources_and_uncertainty`

## Exact reason

The check does not reach `prepare_from_shopify` or any other venture behavior. At line 23, `json.loads(...)` raises `JSONDecodeError: Expecting ',' delimiter: line 2 column 1 (char 477)` while parsing `ventures/fda-cosmetics/tests/acceptance/fixtures/shopify-products-2026-04-16.json`. The fixture has unmatched JSON delimiters at the end of its `data.products.edges` structure. This was reproduced with the requested `--runxfail` command. The fixture and acceptance test are owner-protected by the card instructions, so they were not changed.

## Corrected check

Correct the fixture's closing delimiters so it is valid JSON, then retain the test's existing assertions: pass that parsed GraphQL fixture through the mocked `read_shopify_products`, call `prepare_from_shopify`, and assert the resulting review-ready packet has per-field source metadata and an explicit uncertainty/confirmation marker. The expected ready state should mean ready for owner review only; it must not mean FDA filing-ready or submitted.

Until the fixture is corrected by its owner, this check remains unverified and is not evidence that the Shopify adapter behavior passes.
