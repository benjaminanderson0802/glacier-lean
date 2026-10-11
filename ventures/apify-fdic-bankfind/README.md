# FDIC BankFind Institution Normalizer

**SEO description:** Look up FDIC-insured institutions by certificate or state using the official BankFind API. Get normalized records with source dates, data vintage, and bounded pagination.

Normalize official FDIC bank institutions by certificate or state, with source dates, vintage and bounded pagination.

## Use cases

For vendor-data joins, institution directories and repeatable state snapshots. Filter by certificate and/or state; `active_only` preserves the literal FDIC field rather than inferring safety.

## Input

certificate (string, 1–6 digits) or state (two uppercase letters) is required. Both narrow the search with AND. max_records defaults to 100, maximum 1,000. active_only defaults to false. Internal page_size can be 1–100 for controlled pagination; default 100.

**Example input:**

```json
{
  "certificate": "3510"
}
```

## Output

**Example output:** the source-backed sample below is a recorded local result, not a guarantee of a current record.

One dataset row per one successfully returned institution. `outcome` is `ok`, `no_match` (where the API explicitly reports zero matches), or `uncertain`. Every row includes the official source URL, retrieval time and a plain message. Successful source responses also carry SHA-256 provenance. JSON/CSV/Excel exports are available through Apify dataset downloads; the Output tab includes overview and provenance views.

Actual source-backed sample from 2026-10-11T03:03:34.907171+00:00:

```json
{
  "record_id": "3510",
  "outcome": "ok",
  "billable": true,
  "message": "Official institution record; not a bank safety or deposit coverage determination.",
  "certificate": "3510",
  "name": "Bank of America, National Association",
  "active": true,
  "state": "NC",
  "city": "Charlotte",
  "postal_code": "28202",
  "website": "www.bankofamerica.com",
  "source_updated_at": "2026-06-29",
  "source_vintage": "institutions_20261009090008",
  "source_total": 1,
  "truncated": false,
  "record_url": "https://banks.data.fdic.gov/bankfind-suite/bankfind/details/3510",
  "source_url": "https://api.fdic.gov/banks/institutions?filters=CERT%3A3510&fields=CERT%2CNAME%2CACTIVE%2CSTALP%2CCITY%2CZIP%2CDATEUPDT%2CWEBADDR&format=json&sort_by=CERT&sort_order=ASC&limit=100&offset=0",
  "retrieved_at": "2026-10-11T03:03:36.085759+00:00",
  "source_last_modified": null,
  "source_sha256": "9a185b5ff6750b7b11b53351d5190212af5c7d5fe3cf76cca72d36dd88fbb489"
}
```

Source outages and unreadable/schema-changed responses produce `outcome: "uncertain"`, `billable: false`. Please check the source or retry later. This is never a negative finding.

## Pricing

Suggested pay-per-event price: **$0.002 for one successfully returned institution**, custom event **`bank-record`**. No minimum/start charge; no-match and uncertain results have no custom event charge. Repeated runs can incur new charges; deduplication does not extend across runs. Source data itself is free. `billable` describes event eligibility; local runs never charge.

Configure **only this custom event**, with no automatic `apify-actor-start` or `apify-default-dataset-item` events. The SDK writes a result before charging, uses run-scoped idempotency keys and stops delivery when the event spending limit is reached. Platform idempotency is time-limited; this is not a durable cross-run exactly-once guarantee. Set a maximum total charge in Console; use the input limits to bound source work. Platform compute costs can still apply to the developer even on failed/no-match runs. Pricing configuration is manual; `pricing.json` is a setup reference, not automatic Apify configuration.

Competitor snapshot, 2026-10-10: [pink_comic/fdic-bankfind-search](https://apify.com/pink_comic/fdic-bankfind-search) listed $0.002/result plus $0.0001 start. See [portfolio comparison](../apify-portfolio/CHOICES.md) for fuller evidence and limitations. Proposed price is an experiment, not a promise of profit.

## Limits and source notes

Institution demographics only: no branches, financial series, insurance advice or bank-risk scoring. ZIP and dates can be absent. DATEUPDT is the source record date, not our retrieval date. FDIC can revise its data. Rows flag truncated if matching records exceed max_records; rerun with narrower filters. If a page fails, repeats an ID or changes vintage, the whole snapshot is uncertain and uncharged.

Uses only the [official source](https://api.fdic.gov/banks/docs); see [source-access review](../apify-portfolio/CHOICES.md#source-access-and-reuse-basis). Free public data is attributed; no agency affiliation or endorsement. No UI scraping, login, CAPTCHA bypass or paid dataset. Serial requests are spaced at least one second apart, with 10-second connect/30-second read timeouts, a 5 MB response cap and at most one retry on HTTP 429/503 with a short numeric Retry-After. Longer/date Retry-After values stop the lookup for a later run. Redirects are not followed. The Actor run timeout is 600 seconds, 256 MB by default.

Inputs go to the named agency API as needed for the lookup. Outputs remain in your Apify storage (or your local storage during development); delete runs/datasets using your retention policy. Do not upload secrets or sensitive records.

## Run locally

Use Python 3.12 and the pinned requirements (copied exactly from the existing contractor Actor):

```sh
python -m pip install -r requirements.txt
mkdir -p storage/key_value_stores/default
cp example-input.json storage/key_value_stores/default/INPUT.json
APIFY_IS_AT_HOME=0 CRAWLEE_PURGE_ON_START=false python -m src
```

Use an empty local storage directory or set `APIFY_LOCAL_STORAGE_DIR` to a fresh directory. Do not set an Apify token for local testing. Results are written under `storage/datasets/default`. `apify run` is also supported with the same INPUT. In the Glacier sandbox use `~/w/glacier-lean/.venv/bin/python`.

## Build and publish (owner)

After the commit is integrated into `glacier-final`, Develop new → Connect Git → paste:

`https://github.com/benjaminanderson0802/glacier-lean#glacier-final:ventures/apify-fdic-bankfind`

Build → configure Pay per event with **`bank-record` at $0.002**, without automatic start/dataset charges → review the sample output and Publish. Payout/business verification remains with the owner. This task did not log in, build in the cloud or publish. The Git subfolder is self-contained; it does not import neighboring venture folders.

## Verification

[PROOF.md](PROOF.md) links real local SDK runs and source responses. From the repository root:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/apify-portfolio/tests ventures/tests
~/w/glacier-lean/.venv/bin/python ventures/apify-portfolio/live_canary.py
```
