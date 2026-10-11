# NPI Registry Batch Lookup and Normalizer

**SEO description:** Look up exact NPI numbers in the official CMS NPPES registry. Normalize provider name, primary taxonomy, practice location, and source dates with explicit no-match and uncertainty.

Look up exact NPIs in the official CMS NPPES API. Get names, primary taxonomy, practice location and source dates with explicit no-match and uncertainty.

## Use cases

For cleaning provider-directory joins, checking exact registry IDs supplied by a customer and preparing dated registry exports. Deduplicates the input and selects the practice address and primary taxonomy.

## Input

npis is required: an array of 1–50 ten-digit strings. Validate the NPI check digit before requesting the API. Duplicate IDs produce one request and one result. No name search, patient information, customer API key or login is required.

**Example input:**

```json
{
  "npis": [
    "1881018208"
  ]
}
```

## Output

**Example output:** the source-backed sample below is a recorded local result, not a guarantee of a current record.

One dataset row per one successfully returned provider. `outcome` is `ok`, `no_match` (where the API explicitly reports zero matches), or `uncertain`. Every row includes the official source URL, retrieval time and a plain message. Successful source responses also carry SHA-256 provenance. JSON/CSV/Excel exports are available through Apify dataset downloads; the Output tab includes overview and provenance views.

Actual source-backed sample from 2026-10-11T03:03:38.624902+00:00:

```json
{
  "record_id": "1881018208",
  "npi": "1881018208",
  "outcome": "ok",
  "billable": true,
  "message": "Public NPPES registry record only; not license, exclusion or credential verification.",
  "name": "MAYO CLINIC",
  "enumeration_type": "NPI-2",
  "registry_status": "A",
  "source_updated_at": "2021-04-12",
  "enumeration_date": "2014-02-05",
  "taxonomy_code": "261QM1300X",
  "taxonomy_description": "Clinic/Center, Multi-Specialty",
  "address": "200 1ST ST SW",
  "address_2": null,
  "city": "ROCHESTER",
  "state": "MN",
  "postal_code": "559050001",
  "country_code": "US",
  "warnings": [],
  "record_url": "https://npiregistry.cms.hhs.gov/provider-view/1881018208",
  "source_url": "https://npiregistry.cms.hhs.gov/api/?version=2.1&number=1881018208",
  "retrieved_at": "2026-10-11T03:03:41.402163+00:00",
  "source_last_modified": null,
  "source_sha256": "7ad3d449131f7d8407348e11b2e4d901b7900acf411bd34b072514d6c03a15ac"
}
```

Source outages and unreadable/schema-changed responses produce `outcome: "uncertain"`, `billable: false`. Please check the source or retry later. This is never a negative finding.

## Pricing

Suggested pay-per-event price: **$0.003 for one successfully returned provider**, custom event **`provider-record`**. No minimum/start charge; no-match and uncertain results have no custom event charge. Repeated runs can incur new charges; deduplication does not extend across runs. Source data itself is free. `billable` describes event eligibility; local runs never charge.

Configure **only this custom event**, with no automatic `apify-actor-start` or `apify-default-dataset-item` events. The SDK writes a result before charging, uses run-scoped idempotency keys and stops delivery when the event spending limit is reached. Platform idempotency is time-limited; this is not a durable cross-run exactly-once guarantee. Set a maximum total charge in Console; use the input limits to bound source work. Platform compute costs can still apply to the developer even on failed/no-match runs. Pricing configuration is manual; `pricing.json` is a setup reference, not automatic Apify configuration.

Competitor snapshot, 2026-10-10: [agenscrape/nppes-npi-registry-api](https://apify.com/agenscrape/nppes-npi-registry-api) listed $0.0005/result plus $0.0005 start. See [portfolio comparison](../apify-portfolio/CHOICES.md) for fuller evidence and limitations. Proposed price is an experiment, not a promise of profit.

## Limits and source notes

NPPES public registry only. A valid check digit is not proof that an NPI exists. Enumeration/status is not licensure, credentialing, Medicare participation, sanctions clearance or permission to contact anyone. Source records can be old. No match means only that this exact API query returned no public record. Missing practice address or unique primary taxonomy remains null with warnings; it is not invented. Phone/fax, authorized officials, alternative identifiers and full source records are excluded from output. Never submit patient data.

Uses only the [official source](https://npiregistry.cms.hhs.gov/api-page); see [source-access review](../apify-portfolio/CHOICES.md#source-access-and-reuse-basis). Free public data is attributed; no agency affiliation or endorsement. No UI scraping, login, CAPTCHA bypass or paid dataset. Serial requests are spaced at least one second apart, with 10-second connect/30-second read timeouts, a 5 MB response cap and at most one retry on HTTP 429/503 with a short numeric Retry-After. Longer/date Retry-After values stop the lookup for a later run. Redirects are not followed. The Actor run timeout is 600 seconds, 256 MB by default.

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

`https://github.com/benjaminanderson0802/glacier-lean#glacier-final:ventures/apify-npi-batch`

Build → configure Pay per event with **`provider-record` at $0.003**, without automatic start/dataset charges → review the sample output and Publish. Payout/business verification remains with the owner. This task did not log in, build in the cloud or publish. The Git subfolder is self-contained; it does not import neighboring venture folders.

## Verification

[PROOF.md](PROOF.md) links real local SDK runs and source responses. From the repository root:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/apify-portfolio/tests ventures/tests
~/w/glacier-lean/.venv/bin/python ventures/apify-portfolio/live_canary.py
```
