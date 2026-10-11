# Shopify App Store listing — Glacier FDA Listing

Prepared for the Shopify Partner Dashboard review form. Shopify's form and policy can change; owner should compare this package with the live submission page before submitting.

## Listing identity

- **App name:** Glacier FDA Listing
- **App card subtitle:** Prepare source-linked FDA cosmetics listing drafts.
- **App introduction (100-character field):** Prepare source-linked cosmetic listing drafts while keeping brand decisions in your hands.
- **Primary language:** English
- **Languages supported by the app UI:** English
- **Developer name:** Glacier
- **App icon:** `assets/app-icon-1200.png`
- **Feature media:** `assets/feature-image-1600x900.png`
- **Feature media alt text:** Source-linked cosmetic product review draft from a Shopify catalog, with uncertain fields flagged for brand review.
- **Screenshots:** See `screenshots/` and the alt-text list below.
- **Demo store URL:** https://glacier-test-cosmetics.myshopify.com/ (owner: confirm this exact store URL and reviewer access in Partner Dashboard.)
- **App URL:** `{{APP_BASE_URL}}`
- **Privacy policy URL:** `{{APP_BASE_URL}}/privacy`
- **Support email:** `{{BUSINESS_EMAIL}}`
- **Support channel:** Email
- **Developer website:** `{{APP_BASE_URL}}`
- **Online Store channel required:** No. The app runs in Shopify Admin.
- **Geographic availability:** No store-location restriction. The packet workflow is for U.S. FDA cosmetic product listing records.
- **Test credentials:** No separate Glacier account. The app uses Shopify's merchant authorization. For listing review, install the draft app in Shopify's review store and use the fixture product workflow shown in `review/TESTING-INSTRUCTIONS.md`.
- **App review screencast:** `review/demo-screencast.webm` (English UI labels; fixture-only, no live store or customer data.)
- **Listing visibility:** Public, full visibility (owner confirms in Partner Dashboard.)

## App details (500-character field)

Glacier FDA Listing reads your Shopify catalog to help your responsible person prepare U.S. cosmetic product listing drafts. Add the label, ingredients, FDA category, facility details, and exemption answers. Glacier flags missing or uncertain information and prepares a draft SPL ZIP with 120-day and annual review dates when details are confirmed. Your team reviews and submits filings through FDA Cosmetics Direct. Glacier never signs or submits for you.

## Features (each under 80 characters)

- Read product catalog details without changing Shopify records
- Keep every draft field linked to its catalog, label, or brand source
- Flag missing label, ingredient, category, facility, and exemption details
- Prepare an SPL draft ZIP after the responsible person confirms the fields
- Track 120-day and annual listing review dates
- Leave FDA review, signature, and submission with your responsible person

## Search terms (up to five)

1. FDA cosmetics
2. MoCRA listing
3. cosmetic product listing
4. FDA SPL
5. cosmetic ingredient review

## Categories and structured features

- **Primary category:** Store management → Security → Legal
- **Suggested structured feature:** Compliance reports
- **Shopify integration:** Shopify Admin
- **Additional platform:** FDA Cosmetics Direct (merchant handoff only; no app API connection or submission)

Shopify's taxonomy says Legal apps help merchants with legal compliance. The review team confirms the category and may change it. Similar App Store listings use the Legal category and Compliance reports feature; see competitor evidence below.

## Pricing details

Select **Recurring charge** and configure these monthly Billing API plans:

| Plan | Monthly charge | Included catalog size | Trial | Features |
| --- | ---: | ---: | ---: | --- |
| Starter | $4.99 USD / 30 days | Up to 25 products | 14 days | Read-only catalog, source-linked review checklist, product packet preparation, reminders |
| Studio | $9.99 USD / 30 days | Up to 250 products | 14 days | Starter features for up to 250 products |

- Additional charges: None.
- Annual pricing: None recommended at launch; do not show an annual discount.
- Shopify Billing API: recurring subscriptions; app requests plan approval in Shopify Admin; it does not take payment outside Shopify.
- Price recommendation: $4.99/month Starter, with $9.99/month Studio. These deliberately start below the observed $19/month and $29/month cosmetics-app entry prices. The competitor apps offer different feature sets, so these are directional anchors rather than direct like-for-like pricing.
- Owner price approval required before submission.

## Screenshot alt text

1. **Catalog overview:** Read-only cosmetic product catalog showing product source, Shopify type, and uncertain review state.
2. **Packet preparation:** Brand-review form for product name, ingredient order, label file, facility, responsible person, and exemption answers.
3. **Uncertain result:** Review result identifies fields needing confirmation and states that the app has not signed or submitted an FDA filing.

All images use synthetic fixture data, contain no pricing, reviews, testimonials, outcome guarantees, Shopify marks, or personal data.

## Demo instructions

The demo store is `glacier-test-cosmetics`. Install the app using read_products, open Glacier FDA Listing from Shopify Admin, and review the existing synthetic cosmetic product. The app does not edit Shopify. To demonstrate packet preparation, enter brand-confirmed details and upload the matching ingredient label. If any field or label check is uncertain, the result stays uncertain and no SPL ZIP is made. A completed packet is a draft only; the responsible person decides whether to sign and submit it through Cosmetics Direct.

## Competitor price evidence

Observed 2026-10-11 on the official Shopify App Store pages. Pricing may change. Neither listing proves equivalent functionality to Glacier.

| Listing | Publicly displayed entry price | Relevant product positioning | Evidence |
| --- | ---: | --- | --- |
| Loook Audit | $19/month | Catalog checks for cosmetic ingredients and marketing claims; read-only | [Shopify App Store listing](https://apps.shopify.com/loook-audit) |
| MoCRA Ops Kit | $29/month | Cosmetic label and safety records, status tracking, and review export packs | [Shopify App Store listing](https://apps.shopify.com/mocra-ops-kit) |
| Compliant Copy | $29/month | FDA-aware product-copy review and editing for cosmetics and other regulated products | [Shopify App Store listing](https://apps.shopify.com/compliant-copy) |

The proposed $4.99 starting plan is a low-price entry point to encourage adoption. It is a recommendation, not an approved price or a claim that features are equivalent.

## Official Shopify developer requirements used

- [App Store requirements](https://shopify.dev/docs/apps/launch/shopify-app-store/app-store-requirements)
- [App listing best practices and image requirements](https://shopify.dev/docs/apps/launch/shopify-app-store/best-practices)
- [App listing categories and tags](https://shopify.dev/docs/apps/launch/app-store-review/app-listing-categories)
- [Submit an app for review](https://shopify.dev/docs/apps/launch/app-store-review/submit-app-for-review)
- [Privacy requirements](https://shopify.dev/docs/apps/launch/privacy-requirements)
- [Mandatory privacy webhooks](https://shopify.dev/docs/apps/build/compliance/privacy-law-compliance)
- [Support requirements](https://shopify.dev/docs/apps/launch/distribution/support-your-customers)
- [Shopify Billing API](https://shopify.dev/docs/api/admin-graphql/2026-10/mutations/appSubscriptionCreate)
- [Access scopes](https://shopify.dev/docs/apps/build/authentication-authorization/manage-access-scopes)

## Content checks before submission

- Replace `{{APP_BASE_URL}}` and `{{BUSINESS_EMAIL}}` everywhere.
- Confirm the demo store URL and provide Shopify reviewers access using the Partner Dashboard.
- Confirm the support email is monitored and appears in the Partner Dashboard.
- Check the app name for uniqueness in the live App Store before submission.
- Confirm the category and pricing plan setup in the live form.
- Attach the app icon, feature image, three screenshots, and review screencast.
- Ensure production app URL and privacy URL use HTTPS and are live.
- Add current app review test instructions; there is no separate Glacier username or password.
- Run Shopify's automated review checks, fix any findings, then submit from the Partner Dashboard.
