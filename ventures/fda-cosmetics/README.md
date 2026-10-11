# FDA cosmetics listing preparation

This local Glacier workflow reads a Shopify catalog through the read-only connector and combines it with brand-supplied label, ingredient, category, and facility details. The shared document reader keeps uncertain extraction visible, and the shared FDA rules checker cites the source for each field check. A complete, customer-confirmed record becomes a local SPL ZIP plus a readable checklist. Incomplete or uncertain records do not produce an SPL ZIP.

The brand reviews every value and its small-business exemption checklist. The brand signs where required, uploads the ZIP to FDA Cosmetics Direct, and submits the filing. Glacier never signs or submits to FDA. FDA's portal performs its own initial validation. Save the response returned to the brand and put the forwarded copy in `$GLACIER_HOME/ventures/fda-cosmetics/incoming/fda-response.txt`; then run the response parser below. A parsed acknowledgment is not independent proof of FDA acceptance.

Shopify product details do not include ingredients in the existing read-only connector. Provide `brand-details.json` keyed by Shopify product ID with the product name as printed on the label, product category codes, ingredient names in label order, each facility's FEI or the brand-confirmed exemption and facility address, responsible-person details, first-marketed date, last-listing date, and the brand's confirmations. Never infer ingredients, product category, or exemption status from a product title.

## Your steps

1. Connect a Shopify app with read-only `read_products` access using [Shopify's app setup guide](https://shopify.dev/docs/apps/build), then save credentials through Glacier Secrets. Provide each product's exact label name, label source, ingredient order, category, responsible person, facility FEI/address or confirmed exemption, first-marketed/last-listing dates, and the exemption checklist. Shopify titles are catalog references only; they never stand in for label-confirmed values.
2. Review each packet's field sources, uncertainty flags, ingredient/label checklist, and local 120-day and annual reminders. The responsible person confirms dates and product changes, signs where required, uploads the ZIP to [FDA Cosmetics Direct](https://direct.fda.gov/), and submits any filing or update. Use [FDA Form 5067 instructions](https://www.fda.gov/cosmetics/registration-listing-cosmetic-product-facilities-and-products/form-fda-5067-cosmetic-product-listing) and the [Cosmetics Direct guide](https://direct.fda.gov/apex/f?p=100:103:::::P103_GUIDE:26) when needed. Forward the response into the incoming folder for parsing; Glacier does not claim acceptance unless the response says so.

## Run locally

```sh
~/w/glacier-lean/.venv/bin/python ventures/fda-cosmetics/scripts/listing_prep.py prepare --shop example.myshopify.com --details brand-details.json --output "$GLACIER_HOME/ventures/fda-cosmetics/out"
~/w/glacier-lean/.venv/bin/python ventures/fda-cosmetics/scripts/shopify_owner_check.py example.myshopify.com
~/w/glacier-lean/.venv/bin/python ventures/fda-cosmetics/scripts/listing_prep.py response --file "$GLACIER_HOME/ventures/fda-cosmetics/incoming/fda-response.txt" --output "$GLACIER_HOME/ventures/fda-cosmetics/out/fda-response.json"
~/w/glacier-lean/.venv/bin/python ventures/fda-cosmetics/scripts/listing_prep.py due
~/w/glacier-lean/.venv/bin/python -m pytest ventures/fda-cosmetics -q
```

The owner check calls Shopify's connection metadata and product-read endpoints only. It reports the store and product count without printing catalog records; it does not create, update, publish, or delete Shopify records. The packet records a source for every Form 5067/SPL field. Catalog title is marked uncertain and kept separate from the label name; brand-confirmation fields remain uncertain until explicitly confirmed. The checklist compares parsed label ingredients with the supplied ingredient order and requires the responsible person's confirmation.

The FDA SPL XSD check proves XML structure only. FDA Cosmetics Direct still runs its own technical and business validation. No public data or test payload can verify the brand's ingredients, exemption, facility, FDA response, or filing.

## Data and billing

Customer files should be deleted 30 days after job close unless the customer asks to retain them; automated retention deletion is not yet connected. Product-count subscription pricing is planned but billing remains disabled pending the shared customer layer. No paid integration is required for local packet preparation.
