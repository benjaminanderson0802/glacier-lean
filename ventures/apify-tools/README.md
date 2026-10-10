# Mississippi Contractor License Status

This Apify Actor checks contractor license records published by the Mississippi State Board of Contractors. Enter a license number or business name. Each result includes the board's status, expiration date, source record link, and check time. It repeats the board's wording; it does not decide whether a contractor is legally qualified.

## Run locally

```sh
cd ventures/apify-tools
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
mkdir -p storage/key_value_stores/default
cat > storage/key_value_stores/default/INPUT.json <<'JSON'
{"license_number":"22649"}
JSON
python -m src
```

The Apify SDK reads input from local Actor storage, not standard input. Its output dataset is written under `storage/datasets/default/`. The input schema is `.actor/input_schema.json`.

Batch input accepts up to 100 objects under `queries`, each with either `license_number` or `name`. A name search returns at most 10 records. Requests to the public board search and detail pages are spaced by at least one second. No key, account, browser session, proxy, CAPTCHA, or paid data service is used.

## Apify Store listing and pricing

The publish-ready title, description, keywords, input notes, and owner steps are in `.actor/README.md` and `store_listing.md`. Suggested billing is $0.02 per completed, readable lookup, including readable no-match results. Source outages return `uncertain — please check` with `verification_state: unverifiable` and are not charged. Include platform usage and cap a run at $2.00. Disable Apify's automatic `apify-default-dataset-item` event to avoid duplicate charges.

## Source and limits

The [Mississippi State Board of Contractors public search](https://search.msboc.us/ConsolidatedSearch.cfm) provides contractor search and record detail pages. The board recommends contacting it before taking action because circumstances may change after publication. The Actor returns a point-in-time source result and does not make a legal conclusion. Verify directly with the board before relying on a status.

## Your steps

1. **Your step: Set up the Apify developer and payout account** at [Apify account settings](https://console.apify.com/account/integrations).
2. **Your step: Log in and deploy the Actor.** After account setup, paste this once from the repository root: `cd ventures/apify-tools && npm exec --yes --package=apify-cli@1.10.0 -- apify login && npm exec --yes --package=apify-cli@1.10.0 -- apify push`.
3. **Your step: Publish the first Actor** in [Apify Console](https://console.apify.com/actors) using the listing and $0.02 event price in `.actor/README.md`.
