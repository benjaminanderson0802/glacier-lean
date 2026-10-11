# Glacier FDA Listing — Shopify app draft

Embedded Shopify Admin app scaffolded from Shopify's official React Router template. It reads catalog data through Shopify Admin GraphQL with `read_products`, prepares source-linked FDA cosmetics review packets by calling the existing `ventures/fda-cosmetics` generator in a disposable workspace, and implements Shopify Billing API monthly plans.

The app is a draft. It has no Shopify credentials, production URL, hosted deployment, real store authorization, or FDA submission capability. It does not sign or submit FDA filings. Replace URL and contact placeholders and complete the exact two actions in [listing/OWNER-STEPS.md](listing/OWNER-STEPS.md).

## Requirements

- Node.js 22.12 or newer
- Python 3.12 with the project requirements installed
- Shopify CLI 4.9.3 (installed by npm)
- Shopify Partner app client ID/secret provided only in local runtime environment
- A publicly reachable HTTPS app URL for final review; no host or domain is selected or purchased here

## Local development

1. Run `npm ci` from this folder.
2. From the repository root, install Python requirements used by `ventures/fda-cosmetics` and `ventures/blocks`.
3. Put Shopify app credentials and URL in an untracked `.env` file. Use `PYTHON_EXECUTABLE=~/w/glacier-lean/.venv/bin/python` for the packet bridge.
4. Use `npm run dev` after the owner has linked this folder to the existing Partner app and chosen the `glacier-test-cosmetics` development store. Shopify CLI login and app linking are human/account steps and are not performed by this card.

The listing screenshots are rendered in headless Chromium using the local `GLACIER_DEMO_FIXTURE=true` path. Fixture mode is disabled in production (`NODE_ENV=production`) and displays a visible fixture notice. It does not read a live store.

## Checks

- `npm test`
- `npm run typecheck`
- `npm run build`
- `cd ../.. && ~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/fda-cosmetics ventures/tests`

See [listing/STORE-LISTING.md](listing/STORE-LISTING.md), [listing/PRIVACY-POLICY.md](listing/PRIVACY-POLICY.md), and [listing/review/TESTING-INSTRUCTIONS.md](listing/review/TESTING-INSTRUCTIONS.md).
