# Glacier FDA Listing privacy policy

**Last updated:** October 11, 2026

Glacier FDA Listing reads Shopify product catalog information to prepare cosmetic listing review packets. The app requests only `read_products` access and does not write to Shopify products, orders, customers, or other store records.

## Data we process

The app reads product IDs, titles, handles, product types, tags, and an optional custom ingredients metafield. To prepare a draft, the responsible person may provide the product's label name, ingredient order, FDA category, facility details, exemption answers, responsible-person contact details, marketing/listing dates, and a current ingredient-label file.

Shopify OAuth session data can include Shopify user identifiers, names or email addresses where supplied, and access tokens. The app uses session data only to keep the embedded Shopify Admin app connected.

## Use, sharing, and retention

Catalog data is processed only to display the catalog and prepare the requested draft. Form inputs, uploaded labels, and generated packet files are handled in a temporary workspace and deleted when that request finishes. We do not retain product records, uploaded labels, packet copies, or customer records. Shopify OAuth session data is stored in the app's session database and is accessible to the app server. We do not sell data, use it for advertising, or share it with third parties.

When the app is uninstalled, its Shopify session records are deleted. The app responds to Shopify's `customers/data_request`, `customers/redact`, and `shop/redact` compliance webhooks. No customer records are read or stored.

## Contact

For privacy questions, contact [{{BUSINESS_EMAIL}}](mailto:{{BUSINESS_EMAIL}}).

## Important limits

Glacier produces review drafts and checklists. It does not determine legal exemptions, guarantee compliance, sign for a responsible person, or submit a filing to FDA. The merchant and responsible person review all information and decide what to submit.
