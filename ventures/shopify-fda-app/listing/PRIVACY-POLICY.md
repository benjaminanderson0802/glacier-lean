# Glacier FDA Listing privacy policy draft

**Publication target:** https://andersoneducation.us/privacy-policy
**Status:** Draft for the owner to review and publish. The target page was not reachable when this draft was prepared.
**Last updated:** October 11, 2026

Glacier FDA Listing is an embedded Shopify Admin app that helps a merchant prepare review drafts for U.S. cosmetic product listings. It does not sign or submit FDA filings.

## Information processed

When the app loads, it requests Shopify product IDs, titles, handles, product types, tags, and the optional `custom.ingredients` metafield through Shopify's Admin GraphQL API. The app requests the `read_products` scope and does not write Shopify product, order, or customer records.

When a merchant prepares a packet, the app also processes the fields they enter (product and label name, ingredient order, FDA category, facility and responsible-person details, exemption answers, and marketing/listing dates) and the ingredient-label file they upload. These may include personal contact information and business-confidential information. Shopify OAuth session records may contain the shop domain, Shopify user ID, name, email address, access token, and related session fields needed to keep the app connected.

## How information is used and where it is processed

The app uses catalog and form information only to show the catalog and prepare the packet requested by the merchant. Packet fields and the uploaded label are written to a temporary workspace on the app server while the packet is prepared; the workspace is removed when that request finishes, including when packet preparation fails. The generated packet is returned to the merchant for download and is not saved as an app record. Catalog data is fetched on demand and is not saved as an app record.

Shopify session records are kept in the app's session database while needed for the embedded app connection. They are removed when the app is uninstalled and when Shopify sends a `shop/redact` request. The app acknowledges Shopify's `customers/data_request` and `customers/redact` webhooks; the app does not collect Shopify customer records.

The production hosting provider, server location, and its retention or backup behavior have not been selected or verified. Before publishing this policy, the owner must identify the production host and update this section with any provider that can access app data and the applicable storage location/retention facts. Data must pass through the production app host to prepare a packet. Shopify processes authorization and billing actions under Shopify's own terms and privacy policy.

We do not use this information for advertising or sell it. No other third-party data-sharing arrangement has been configured in the app code reviewed for this draft.

## Contact and requests

For privacy questions or a request about app data, contact **{{BUSINESS_EMAIL}}** at [mailto:{{BUSINESS_EMAIL}}](mailto:{{BUSINESS_EMAIL}}). The owner must replace this placeholder with a monitored address before publishing.
Business mailing address, if required for the operator and applicable jurisdiction: **{{BUSINESS_ADDRESS — owner to confirm}}**.

Shopify's privacy requirements may require additional disclosures or data-rights procedures depending on the operator, users, and jurisdictions. The owner must review this draft against the actual production setup and applicable requirements before publishing; this draft does not determine legal obligations.

## Product and filing limits

Glacier prepares review drafts and checklists. It does not decide legal exemptions, guarantee compliance, sign for a responsible person, or submit a filing to FDA. The merchant and responsible person review all information and decide what to submit.
