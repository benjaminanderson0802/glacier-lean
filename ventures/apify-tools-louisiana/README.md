# Louisiana Contractor License Status

This standalone Apify Actor checks contractor license records published by the Louisiana State Licensing Board for Contractors. Enter a license number such as `CL.68755` or a company-name substring of at least three characters. Each result includes the license type, literal board status, effective and expiration dates, official detail link, and UTC check time. The Actor repeats the board's wording and does not decide whether a contractor is legally qualified.

The lifecycle uses the reusable runner copied into `src/actor_template.py`; `src/lookup.py` contains only Louisiana source access and parsing. The package is deployable directly from this Git subfolder.

## Run locally

```sh
cd ventures/apify-tools-louisiana
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
mkdir -p storage/key_value_stores/default
cat > storage/key_value_stores/default/INPUT.json <<'JSON'
{"license_number":"CL.68755"}
JSON
python -m src
```

The Apify SDK reads input from Actor storage, not standard input. Output is written to `storage/datasets/default/`. Batch input accepts up to 100 objects under `queries`; each has either `license_number` or `name`. Name searches return at most 10 matching licenses. Every search and detail request is spaced by at least one second. The adapter does not use a login, key, browser session, proxy, CAPTCHA, or paid data service.

## Source and limits

The [LSLBC contractor search page](https://lslbc.louisiana.gov/contractor-search/) links to its [public number search](https://arlspublic.lslbc.louisiana.gov/Public/DetailedSearch/ByNumber) and [public company-name search](https://arlspublic.lslbc.louisiana.gov/Public/DetailedSearch/ByName). The search portal is reachable without an account. Company searches require three or more characters; the source caps broad search result pages at 1,500 records, and this Actor returns at most 10 matching licenses. Results preserve the board's status and date wording after normalization. Verify directly with LSLBC before relying on a point-in-time result. This independent Actor is not affiliated with or endorsed by LSLBC.

## Listing and price

The prepared title, description, terms, search words, source note, and support text are in [store_listing.md](store_listing.md). Suggested billing is $0.02 per completed readable lookup, including readable no-match results. Source outages are not charged. Include platform usage and set a $2.00 maximum charge per run. Disable the automatic `apify-default-dataset-item` event.

## Owner-only steps

1. Set up the Apify developer and payout account, log in with the official Apify CLI, and upload this subfolder yourself.
2. Run the Louisiana-specific Glacier publication approval after reviewing the no-blocking distinct-engine review in [`REVIEW.md`](REVIEW.md); then publish the Actor yourself in Apify Console. No account, payout setup, upload, or publication was performed for this draft.
