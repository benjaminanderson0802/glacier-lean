# Proof — FDA cosmetics listing preparation

## Acceptance checks

- `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/fda-cosmetics/tests` — **8 passed**.
- `~/w/glacier-lean/.venv/bin/python ventures/install_all.py --only fda-cosmetics --dry-run` — both flows validated.
- A synthetic, customer-confirmed payload produced a local SPL ZIP; `lxml.etree.XMLSchema` validated its XML against FDA's published `SPL.xsd`: **`FDA SPL XSD valid: True`**. FDA's current SPL resources page links the 2016 schema package. This checks XML structure only; Cosmetics Direct performs additional validation.

The focused tests now create the label path required by `_reader_review`; the production code was right to stop on a missing source document. A new malformed-label test verifies that the shared document reader's format-specific exception becomes an uncertain customer-review result rather than an uncaught crash. Complete confirmed fields create a packet, incomplete/uncertain fields do not, dates register 120-day and annual reminders, and the customer remains the only signer and submitter.

## Current limits

No real Shopify credentials, brand label, product catalog, Cosmetics Direct response, or FDA filing was available. The synthetic payload and schema check do not prove the FDA portal accepts a submission. Forwarded FDA responses remain customer-provided records for parsing. Automated 30-day retention deletion and customer-layer billing are not connected and remain launch dependencies.

The separate imported-reader disagreement behavior is still assigned to the shared reader owner under claim `CLM-2026-10-10-PH12-15-READER-CONFLICT-CONTRACT`; it is outside this venture card. No NORTHSTAR checkpoint status was changed.

## FDA references

- [Form FDA 5067](https://www.fda.gov/cosmetics/registration-listing-cosmetic-product-facilities-and-products/form-fda-5067-cosmetic-product-listing)
- [SPL Implementation Guide with Validation Procedures](https://www.fda.gov/media/84201/download)
- [FDA SPL schema and resources](https://www.fda.gov/industry/fda-data-standards-advisory-board/structured-product-labeling-resources)
- [Cosmetics Direct](https://www.fda.gov/cosmetics/registration-listing-cosmetic-product-facilities-and-products/cosmetics-direct)
