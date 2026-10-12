# Product Recall Checker (CPSC, NHTSA, FDA)

**Store title:** Product Recall Checker (CPSC, NHTSA, FDA)
**SEO description:** Check product names, barcodes, brands, models, and vehicle details against public CPSC, NHTSA, and FDA recall records. Get source links, per-source status, and dated results.
**Example input:** `{"brand":"Fisher-Price","product_name":"Rock 'n Play Sleeper"}`
**Example output:** `{"outcome":"uncertain","message":"uncertain — please check (CPSC, FDA-food, FDA-drug, FDA-device unavailable)","query":{"brand":"Fisher-Price","product_name":"Rock 'n Play Sleeper"},"matches":[],"sources_checked":{"CPSC":{"status":"error"},"FDA-food":{"status":"error"},"FDA-drug":{"status":"error"},"FDA-device":{"status":"error"}},"checked_at":"2026-10-11T02:00:00Z"}` (illustrative outage shape, not a current live check).
**Price:** `$0.01` per `recall-check`; outage-only output is free, partial/source-backed results are charged. Include platform usage and disable automatic start/dataset-item charges. See [publish checklist](../apify-portfolio/PUBLISH-CHECKLIST.md).


This Python Apify Actor checks one product or a batch of up to 100 against public recall records from the U.S. Consumer Product Safety Commission (CPSC), National Highway Traffic Safety Administration (NHTSA), and FDA openFDA food, drug, and device enforcement data. It returns a result for each item with links to the source records.

Results use three outcomes:

- `match`: an exact barcode/UPC match or a normalized brand-and-model match was found.
- `no_match`: no matching record was found in the sources checked as of the date shown.
- `uncertain`: a source was unavailable, the item details were too limited, or a possible match needs a person to review.

An unavailable source never becomes a clean `no_match`. Each source has its own status and UTC check time. Verify an important result on the official source before acting. This checker is not a legal conclusion or a complete guarantee that a product is safe.

## Run locally

```sh
cd ventures/recall-actor
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m pytest tests -q
mkdir -p storage/key_value_stores/default
cat > storage/key_value_stores/default/INPUT.json <<'JSON'
{"barcode":"012345678905","brand":"Example","model":"H-100","product_name":"Example heater"}
JSON
python -m src
```

One item can use `barcode`, `brand`, `model`, `product_name`, and optional vehicle `year`. Use `queries` for a batch of 1–100 item objects. NHTSA checks require a vehicle make, model, and year; without all three, that source is marked skipped. Requests use official public endpoints, short timeouts, bounded retries, and a polite request interval. No API keys or paid data sources are used.

## Output and billing

Each dataset item contains `outcome`, `message`, `query`, `matches`, `sources_checked`, and `checked_at`. Every match has `source`, `recall_id`, `title`, `date`, `hazard`, `remedy`, and `url`. `no_match` uses the wording `no match found in [sources] as of [date]`; uncertain results say `uncertain — please check` and identify failed sources.

The configured event is `$0.01` per completed query. A result consisting only of source outages is not charged. A partial result is charged if at least one source responded. Apify platform usage is included in the event configuration; configure a maximum run charge and disable the automatic `apify-default-dataset-item` event before publication.

## Sources and limits

- CPSC recalls: [SaferProducts.gov Recall API](https://www.saferproducts.gov/RestWebServices/Recall?format=json)
- NHTSA vehicle recalls: [NHTSA API](https://api.nhtsa.gov/recalls/recallsByVehicle)
- FDA recalls: [openFDA food enforcement](https://api.fda.gov/food/enforcement.json), [drug enforcement](https://api.fda.gov/drug/enforcement.json), and [device enforcement](https://api.fda.gov/device/enforcement.json)

The public datasets may be incomplete, delayed, or changed by their publishers. Barcode matching depends on an official record containing the same identifier. Brand and model matching is deliberately strict; similar or incomplete details remain uncertain. This version does not search FSIS.

## Chrome extension

The extension defaults to the local Glacier API. In the popup, choose **hosted Apify Actor** to enter an Actor ID and an Apify API token. The token is stored in `chrome.storage.local` in that browser. Hosted checks send only the barcode, brand, model, and product name fields to Apify's run-sync endpoint. The extension reads the current page only when the user clicks **read this page**; it does not crawl a marketplace.

## Your steps

The standalone Actor package is ready for the owner’s account actions. Update existing Actor `Fpv0233nJE7VxcgfN`; do not create a duplicate. Complete account verification once, then connect this Git subfolder, build it, set `recall-check` to `$0.01`, review the source-status output, and publish in the same sitting as the other five Actors. The exact values and Console links are in the [portfolio publish checklist](../apify-portfolio/PUBLISH-CHECKLIST.md); see [owner steps](OWNER-STEPS.md).

The Git URL targets `glacier-final` and becomes available after this commit is integrated. No account, payout setup, cloud build, charge, or publication was performed for this draft.

## Verification status

The offline test suite uses recorded response fixtures for CPSC, NHTSA, and FDA food, drug, and device shapes. The optional live canary is skipped by default. The tests do not verify Actor deployment or public publication.

Current builder verification is recorded in [PROOF.md](PROOF.md), including the exact acceptance and venture-suite commands. The canary was not run for that verification, so it makes no live-source accuracy claim.

The standalone Store package has fixture-based behavior checks, but this verification does not claim a 1,000-item accuracy benchmark or a current live-source canary. Review the shown source states and official notices before relying on an individual result. The separate Recall Checker workflow retains its own open source and release gates.
