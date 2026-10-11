# Contractor License Status — Mississippi and Louisiana

These independent Apify Actors check public contractor license records in Mississippi and Louisiana. Each result includes the board's status, expiration date, source record link, and check time. The Actors repeat the board's wording; they do not decide whether a contractor is legally qualified. Mississippi's deployable package is in this folder. Louisiana's is in [`../apify-tools-louisiana/`](../apify-tools-louisiana/).

Both Actor lifecycles use the reusable runner in `src/actor_template.py`; each board adapter supplies normalized inputs and public-source lookup behavior. Follow `BOARD_REVIEW.md` for every board. Louisiana has live canary evidence and a no-blocking distinct-engine code and Store-listing review in [`../apify-tools-louisiana/REVIEW.md`](../apify-tools-louisiana/REVIEW.md); its owner publication approval remains pending.

## Run Mississippi locally

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

The Apify SDK reads input from local Actor storage, not standard input. Its output dataset is written under `storage/datasets/default/`. Each package has an independent `.actor/input_schema.json`.

## Apify Store listing and pricing

The publish-ready text is in each package's `.actor/README.md` and `store_listing.md`. Suggested billing is $0.02 per completed readable lookup, including readable no-match results. Source outages return `uncertain — please check` with `verification_state: unverifiable` and are not charged. Include platform usage and cap each run at $2.00. Disable Apify's automatic `apify-default-dataset-item` event to avoid duplicate charges.

## Sources and limits

- [Mississippi State Board of Contractors public search](https://search.msboc.us/ConsolidatedSearch.cfm)
- [Louisiana State Licensing Board for Contractors search page](https://lslbc.louisiana.gov/contractor-search/) and its [official search portal](https://arlspublic.lslbc.louisiana.gov/Public/DetailedSearch/ByNumber)

The Louisiana search is publicly reachable without an account and supports company-name and license-number lookups. Live probes found a three-character minimum for company-name searches and a 1,500-row source cap for broad searches; the Actor returns at most 10 matches. Both adapters space source requests at least one second apart. Verify directly with the board before relying on a point-in-time result. Neither Actor is affiliated with or endorsed by its board.

## Your steps

1. **Your step: Set up your Apify developer and payout account, then deploy both Actors.** Complete account setup at [Apify account settings](https://console.apify.com/account/integrations). Install the CLI and run `npm exec --yes --package=apify-cli@1.10.0 -- apify login`, then upload each package with `(cd ventures/apify-tools && npm exec --yes --package=apify-cli@1.10.0 -- apify push)` and `(cd ventures/apify-tools-louisiana && npm exec --yes --package=apify-cli@1.10.0 -- apify push)`.
2. **Your step: Review and publish each listing separately.** Run a separate Glacier approval per Actor. A different engine must review that Actor's code and Store listing; then publish it yourself in [Apify Console](https://console.apify.com/actors), using the reviewed price and billing settings. Mississippi and Louisiana approvals cannot be reused. Louisiana must not be published until its separate-engine review is recorded.
