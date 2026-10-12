# Contractor License Status — Mississippi and Louisiana

**Store title:** Mississippi Contractor License Status
**SEO description:** Look up Mississippi contractor license status and expiration from public Mississippi State Board of Contractors records. Search by license number or business name and export source-linked results.
**Example input:** `{"license_number":"22649"}`
**Example output:** `{"outcome":"match","verification_state":"verified","license_number":"22649","business_name":"10TENCONSTRUCTION, LLC","status":"Licensed","expiration_date":"2027-05-07","source_url":"https://search.msboc.us/Detail.cfm?ContractorID=54380&ContractorType=Residential&varDataSource=BOCRes","checked_at":"2026-10-10T05:29:46+00:00"}` (recorded local output; historical, not current-status evidence).
**Price:** `$0.02` per `license-lookup`; readable no-match is billable, source outage is not. Include platform usage and disable automatic start/dataset-item charges. See [publish checklist](../apify-portfolio/PUBLISH-CHECKLIST.md).


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

The Mississippi and Louisiana Store packages are ready. Complete account verification once, then update both existing Actors in one sitting using the exact links and values in [the portfolio publish checklist](../apify-portfolio/PUBLISH-CHECKLIST.md). Do not create duplicates. See [owner steps](OWNER-STEPS.md).

The required owner actions are account/payout verification, connecting each Git subfolder, starting each build, setting the listed event price and run cap, reviewing the build/output, and publishing each listing. The URLs target `glacier-final` and become available after this commit is integrated.
