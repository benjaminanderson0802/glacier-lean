# Census Building Permits State Change Feed

**SEO description:** Compare official monthly Census state residential building permit estimates. Preserve FIPS, reported versus imputed units, valuation units, source vintages, and period changes.

Compare official monthly state residential building permit estimates, preserving FIPS, source snapshots, imputation and dollar units.

## Use cases

For construction-market reporting, supplier territory comparisons and recurring monthly dashboards. Compare two explicitly selected periods or discover the latest official monthly release automatically.

## Input

period is YYYY-MM (2000–2099) or latest (default). previous_period defaults to the preceding calendar month. states is an array of two-digit FIPS strings; empty means 50 states and DC. Example ["01","22","28"] selects Alabama, Louisiana and Mississippi.

**Example input:**

```json
{
  "period": "2026-08",
  "previous_period": "2026-07",
  "states": [
    "01",
    "22",
    "28"
  ]
}
```

## Output

**Example output:** the source-backed sample below is a recorded local result, not a guarantee of a current record.

One dataset row per one state successfully compared across both periods. `outcome` is `ok`, `no_match` (where the API explicitly reports zero matches), or `uncertain`. Every row includes the official source URL, retrieval time and a plain message. Successful source responses also carry SHA-256 provenance. JSON/CSV/Excel exports are available through Apify dataset downloads; the Output tab includes overview and provenance views.

Actual source-backed sample from 2026-10-11T03:03:36.311216+00:00:

```json
{
  "record_id": "01:2026-08:2026-07",
  "state_fips": "01",
  "name": "Alabama",
  "outcome": "ok",
  "billable": true,
  "message": "Period-to-period change in estimates including imputation; not individual permit leads or a revision flag.",
  "period": "2026-08",
  "previous_period": "2026-07",
  "units": 1731,
  "previous_units": 1560,
  "units_change": 171,
  "units_change_pct": 10.9615,
  "valuation_usd": 451645000,
  "previous_valuation_usd": 458819000,
  "valuation_change_usd": -7174000,
  "reported_units": 1318,
  "previous_source_url": "https://www2.census.gov/econ/bps/State/st2607c.txt",
  "previous_source_sha256": "1d708a0915a80f1814356d851cd781fdb39151782ee1c893bf2d1ada51a7a24f",
  "previous_source_last_modified": "Tue, 25 Aug 2026 12:00:45 GMT",
  "source_url": "https://www2.census.gov/econ/bps/State/st2608c.txt",
  "retrieved_at": "2026-10-11T03:03:37.205932+00:00",
  "source_last_modified": "Thu, 24 Sep 2026 11:46:16 GMT",
  "source_sha256": "029fe001b8ff893a5b053e9511f86fb90d18bc9e390ad9488fcd271c7e37bc86"
}
```

Source outages and unreadable/schema-changed responses produce `outcome: "uncertain"`, `billable: false`. Please check the source or retry later. This is never a negative finding.

## Pricing

Suggested pay-per-event price: **$0.002 for one state successfully compared across both periods**, custom event **`state-comparison`**. No minimum/start charge; no-match and uncertain results have no custom event charge. Repeated runs can incur new charges; deduplication does not extend across runs. Source data itself is free. `billable` describes event eligibility; local runs never charge.

Configure **only this custom event**, with no automatic `apify-actor-start` or `apify-default-dataset-item` events. The SDK writes a result before charging, uses run-scoped idempotency keys and stops delivery when the event spending limit is reached. Platform idempotency is time-limited; this is not a durable cross-run exactly-once guarantee. Set a maximum total charge in Console; use the input limits to bound source work. Platform compute costs can still apply to the developer even on failed/no-match runs. Pricing configuration is manual; `pricing.json` is a setup reference, not automatic Apify configuration.

Competitor snapshot, 2026-10-10: [aether_studio/census-state-building-permit-change-monitor](https://apify.com/aether_studio/census-state-building-permit-change-monitor) listed $0.001/result plus $0.005 start. See [portfolio comparison](../apify-portfolio/CHOICES.md) for fuller evidence and limitations. Proposed price is an experiment, not a promise of profit.

## Limits and source notes

State monthly residential aggregates only, not addresses or individual permits. Estimates include imputation; reported_units is separate. Valuations are converted from source thousands to USD. Percent change is null for a zero prior denominator. No annual/YTD comparison, seasonal adjustment, forecast or revision classification. Source files can be revised in place; hashes and Last-Modified record the retrieved vintage. No missing value is replaced by zero. A missing month/changed schema yields uncertain; a missing state/value yields a free uncertain row. Latest means latest published file, not the current month.

Uses only the [official source](https://www.census.gov/construction/bps/index.html); see [source-access review](../apify-portfolio/CHOICES.md#source-access-and-reuse-basis). Free public data is attributed; no agency affiliation or endorsement. No UI scraping, login, CAPTCHA bypass or paid dataset. Serial requests are spaced at least one second apart, with 10-second connect/30-second read timeouts, a 5 MB response cap and at most one retry on HTTP 429/503 with a short numeric Retry-After. Longer/date Retry-After values stop the lookup for a later run. Redirects are not followed. The Actor run timeout is 600 seconds, 256 MB by default.

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

`https://github.com/benjaminanderson0802/glacier-lean#glacier-final:ventures/apify-census-permits`

Build → configure Pay per event with **`state-comparison` at $0.002**, without automatic start/dataset charges → review the sample output and Publish. Payout/business verification remains with the owner. This task did not log in, build in the cloud or publish. The Git subfolder is self-contained; it does not import neighboring venture folders.

## Verification

[PROOF.md](PROOF.md) links real local SDK runs and source responses. From the repository root:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/apify-portfolio/tests ventures/tests
~/w/glacier-lean/.venv/bin/python ventures/apify-portfolio/live_canary.py
```
