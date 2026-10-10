# Recall checker

Recall checker looks up products against the local Glacier feed database for CPSC, NHTSA, FDA and FSIS recall records. It can check an item in the Chrome tab you opened, process a store inventory CSV, or answer a local JSON API request. A result is **match**, **no match found in CPSC, NHTSA, FDA and FSIS as of [date]**, or **uncertain — please check**. A match links to the official source record. An unavailable or stale feed makes the result uncertain.

The extension reads the current tab only after you click **read this page**. It never crawls a marketplace. It extracts a barcode, brand and model in the browser and sends only those fields to the API on `127.0.0.1`; the page text is not sent or saved. Start the local API from the repository root with:

```sh
/home/glacier/w/glacier-lean/.venv/bin/python ventures/recall-checker/scripts/api.py
```

Refresh public recall data and create one local HTML page for each feed record with the scheduled **Refresh recall data and pages** flow. Pages remain local under `$GLACIER_HOME/ventures/recall-checker/pages/`. The first-page review flow checks all four sources before asking you to review the first 50. Review the source links before you choose any public host.

For a store, place `inventory.csv` in `$GLACIER_HOME/ventures/recall-checker/incoming/` and run **Check a store inventory file**. The output is a separate flagged CSV in `outputs/`; the original is not changed. API clients can send `POST /api/match` with JSON such as `{"item":{"barcode":"012345678905","brand":"Example","model":"BL-100"}}`. The API listens on loopback only at `http://127.0.0.1:8765` and does not require a key because it is not exposed to the network.

## Plans

The free tier covers single lookups. `plans.json` records the spec's individual range ($5–9/month), store range ($29–79/month), and metered API plan. Checkout is not active until you set test price IDs and a Stripe test key in Glacier Secrets. The shared customer block refuses live Stripe keys. Choose exact prices and enable any live billing yourself.

## Your steps

1. Review the first 50 generated pages before placing any on a public site.
2. Review and submit the Chrome Web Store listing and extension package.
3. Configure test prices and review plan wording before offering paid access.

## Current limits

Exact barcode/model matches are automatic. Similar brand/model cases return **uncertain — please check**; this version does not invoke local and second-engine model judges. The required labeled 500 recalled and 500 clean benchmark has not been provided, so no accuracy release claim is made and public rollout remains gated. The reader and rules shared packages are absent from this branch; recall matching is a small venture-local function and does not edit a shared block.

## Extension package

Load `extension/` through `chrome://extensions` → **Developer mode** → **Load unpacked** for owner review. The directory is Manifest V3 and requests only `activeTab`, `scripting`, and access to the loopback API. The Chrome Web Store listing and submission remain owner steps.
