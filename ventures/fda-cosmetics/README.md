# FDA cosmetics listing preparation

This local Glacier workflow reads a Shopify catalog through the read-only connector and combines it with brand-supplied label, ingredient, category, and facility details. The shared document reader keeps uncertain extraction visible, and the shared FDA rules checker cites the source for each field check. A complete, customer-confirmed record becomes a local SPL ZIP plus a readable checklist. Incomplete or uncertain records do not produce an SPL ZIP.

The brand reviews every value and its small-business exemption checklist. The brand signs where required, uploads the ZIP to FDA Cosmetics Direct, and submits the filing. Glacier never signs or submits to FDA. FDA's portal performs its own initial validation. Save the response returned to the brand and put the forwarded copy in `$GLACIER_HOME/ventures/fda-cosmetics/incoming/fda-response.txt`; then run the response parser below. A parsed acknowledgment is not independent proof of FDA acceptance.

Shopify product details do not include ingredients in the existing read-only connector. Provide `brand-details.json` keyed by Shopify product ID with the product name as printed on the label, product category codes, ingredient names in label order, each facility's FEI or the brand-confirmed exemption and facility address, responsible-person details, first-marketed date, last-listing date, and the brand's confirmations. Never infer ingredients, product category, or exemption status from a product title.

## Your steps

1. Create a Shopify app with read-only `read_products` access using [Shopify's app setup guide](https://shopify.dev/docs/apps/build). Save credentials through Glacier Secrets. For each product, provide the source label and brand-confirmed ingredients, category, responsible person, facility FEI/address or confirmed exemption, first-marketed date, last-listing date, and the three-item exemption checklist.
2. Review the complete SPL ZIP and source checklist. The responsible person signs where needed, uploads the ZIP to [FDA Cosmetics Direct](https://direct.fda.gov/), and submits it. Use the [FDA Form 5067 instructions](https://www.fda.gov/cosmetics/registration-listing-cosmetic-product-facilities-and-products/form-fda-5067-cosmetic-product-listing) if any field is unclear. Forward the response into the local incoming folder for parsing; Glacier does not claim FDA accepted a listing unless the response says so.
3. Check the local deadline reminders each day. FDA says an initial listing for a product first marketed after December 29, 2022 is due within 120 days of first marketing, and product listing updates are due annually. Confirm those dates and any changes with the responsible person using [FDA's Cosmetics Direct guide](https://direct.fda.gov/apex/f?p=100:103:::::P103_GUIDE:26). The responsible person decides, signs, and submits each update.

## Run locally

```sh
~/w/glacier-lean/.venv/bin/python ventures/fda-cosmetics/scripts/listing_prep.py prepare --shop example.myshopify.com --details brand-details.json --output "$GLACIER_HOME/ventures/fda-cosmetics/out"
~/w/glacier-lean/.venv/bin/python ventures/fda-cosmetics/scripts/listing_prep.py response --file "$GLACIER_HOME/ventures/fda-cosmetics/incoming/fda-response.txt" --output "$GLACIER_HOME/ventures/fda-cosmetics/out/fda-response.json"
~/w/glacier-lean/.venv/bin/python ventures/fda-cosmetics/scripts/listing_prep.py due
~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/fda-cosmetics/tests
```

The FDA SPL XSD check proves XML structure only. FDA Cosmetics Direct still runs its own technical and business validation. No public data or test payload can verify the brand's ingredients, exemption, facility, FDA response, or filing.

## Data and billing

Customer files should be deleted 30 days after job close unless the customer asks to retain them; automated retention deletion is not yet connected. Product-count subscription pricing is planned but billing remains disabled pending the shared customer layer. No paid integration is required for local packet preparation.
