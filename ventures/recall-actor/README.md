# Product Recall Checker (CPSC, NHTSA, FDA)

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

1. Set up your Apify developer and payout account, then deploy the Actor from this folder.
2. In Apify Console, set the `recall-check` event to `$0.01`, choose a maximum total run charge, and disable the default dataset-item event.
3. Review the listing and source behavior before making the Actor public. Check official notices directly when a result matters.

## Verification status

The offline test suite uses recorded response fixtures for CPSC, NHTSA, and FDA food, drug, and device shapes. The optional live canary is skipped by default. This repository has not deployed or published this Actor.
