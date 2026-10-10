# FDA cosmetics listing preparation

This local Glacier workflow reads a Shopify catalog through the read-only Shopify connector, then combines it with brand-supplied label, ingredient, category, and facility details. The shared document reader keeps uncertain extraction visible, and the shared FDA rules checker cites the source for each field check. A complete, customer-confirmed record becomes a local SPL ZIP plus a readable checklist. Incomplete or uncertain records do not produce an SPL ZIP.

The brand reviews every value and the small-business exemption checklist. The brand signs where needed, uploads the ZIP to FDA Cosmetics Direct, and submits the filing. Glacier never signs or sends a filing to FDA. FDA's portal performs its own initial validation, so the owner/customer must review any FDA response and forward it for local parsing.

Shopify product details do not include ingredients in the existing read-only connector. Provide `brand-details.json` keyed by Shopify product ID with the product name as printed on the label, product category codes, ingredient names in label order, each facility's FEI or the brand-confirmed exemption and facility address, responsible-person details, and the brand's confirmation. Never infer ingredients, product category, or exemption status from a product title.

## Your steps

1. Create the Shopify app with `read_products`, save its credentials through Glacier Secrets, and provide the product/facility details.
2. Review the packet and confirm every extracted ingredient and exemption item.
3. Sign where required and upload the ZIP to FDA Cosmetics Direct; complete Shopify app review before public launch.

## Data and billing

Products and uploaded records remain on the Glacier machine and should be removed within 30 days after the job closes unless the customer asks to retain them. Subscription pricing is planned by product count; billing remains disabled pending the owner-configured customer layer. No paid integration is required for this preparation workflow.
