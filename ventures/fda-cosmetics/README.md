# FDA cosmetics listing preparation

**Release status: blocked.** The fixture flows now run through Glacier, but automatic 30-day retention deletion and customer-layer billing are not connected. The shared reader claim still needs its assigned owner to reconcile it with the currently passing check. Your step is to connect Shopify, provide brand-confirmed product and label facts, review the packet, and have the responsible person sign and submit any filing.

This local Glacier workflow reads a Shopify catalog through the read-only connector and combines it with brand-supplied label, ingredient, category, and facility details. The shared document reader keeps uncertain extraction visible, and the shared FDA rules checker cites the source for each field check. A complete, customer-confirmed record becomes a local SPL ZIP plus a readable checklist. Incomplete or uncertain records do not produce an SPL ZIP.

The brand reviews every value and its small-business exemption checklist. The brand signs where required, uploads the ZIP to FDA Cosmetics Direct, and submits the filing. Glacier never signs or submits to FDA. FDA's portal performs its own initial validation. Save the response returned to the brand and put the forwarded copy in `$GLACIER_HOME/ventures/fda-cosmetics/incoming/fda-response.txt`; then run the response parser below. A parsed acknowledgment is not independent proof of FDA acceptance.

Shopify product details do not include ingredients in the existing read-only connector. Provide `brand-details.json` keyed by Shopify product ID with the product name as printed on the label, product category codes, ingredient names in label order, each facility's FEI or the brand-confirmed exemption and facility address, responsible-person details, first-marketed date, last-listing date, and the brand's confirmations. Never infer ingredients, product category, or exemption status from a product title.

## Your step

Connect Shopify with read-only `read_products` access and enter the exact label name, source label, ingredient order, product category, responsible person, facility FEI/address or confirmed exemption, marketing/listing dates, and exemption checklist for each product. Review the source-linked packet and reminders; the responsible person signs where required and submits any filing through [FDA Cosmetics Direct](https://direct.fda.gov/), then forwards the response for local parsing. Use [Shopify's app setup guide](https://shopify.dev/docs/apps/build), [FDA Form 5067 instructions](https://www.fda.gov/cosmetics/registration-listing-cosmetic-product-facilities-and-products/form-fda-5067-cosmetic-product-listing), and the [February 2026 Cosmetics Direct guide](https://www.fda.gov/media/191059/download) when needed. Glacier does not publish the app, sign, or submit to FDA.

## Run locally

The owner reports that the Shopify development store `glacier-test-cosmetics` is connected. That connection does not supply brand-confirmed ingredients, label, facility, or responsible-person details. No live product packet, Cosmetics Direct response, FDA acceptance, or filing has been verified.

```sh
~/w/glacier-lean/.venv/bin/python ventures/fda-cosmetics/scripts/listing_prep.py prepare --shop example.myshopify.com --details brand-details.json --output "$GLACIER_HOME/ventures/fda-cosmetics/out"
~/w/glacier-lean/.venv/bin/python ventures/fda-cosmetics/scripts/shopify_owner_check.py example.myshopify.com
~/w/glacier-lean/.venv/bin/python ventures/fda-cosmetics/scripts/listing_prep.py response --file "$GLACIER_HOME/ventures/fda-cosmetics/incoming/fda-response.txt" --output "$GLACIER_HOME/ventures/fda-cosmetics/out/fda-response.json"
~/w/glacier-lean/.venv/bin/python ventures/fda-cosmetics/scripts/listing_prep.py due --output "$GLACIER_HOME/ventures/fda-cosmetics/out/due-reminders.json"
~/w/glacier-lean/.venv/bin/python -m pytest ventures/fda-cosmetics -q
```

The owner check calls Shopify's connection metadata and product-read endpoints only. It reports the store and product count without printing catalog records; it does not create, update, publish, or delete Shopify records. The packet records a source for every Form 5067/SPL field. Catalog title is marked uncertain and kept separate from the label name; brand-confirmation fields remain uncertain until explicitly confirmed. The checklist compares parsed label ingredients with the supplied ingredient order and requires the responsible person's confirmation.

The `prepare_from_shopify(shop, details_path, output_dir)` adapter also supports an owner-review preview directly from Shopify GraphQL product records. It labels that preview `ready` only for review, keeps `filing_ready` and `submitted` false, and marks catalog-only or brand-dependent values uncertain.

The FDA SPL XSD check proves XML structure only. FDA Cosmetics Direct still runs its own technical and business validation. The FDA's [SPL implementation guide](https://www.fda.gov/media/84201/download) includes the cosmetics product section (chapter 3.4), but it does not establish any brand's ingredients, exemption, facility, FDA response, or filing.

The fixture engine run and current acceptance results are recorded in [PROOF.md](PROOF.md). The Shopify fixture and all brand/product facts used in that run are synthetic; no live Shopify data or FDA filing was used.

## Data and billing

Customer files should be deleted 30 days after job close unless the customer asks to retain them; automated retention deletion is not yet connected. Product-count subscription pricing is planned but billing remains disabled pending the shared customer layer. No paid integration is required for local packet preparation.
