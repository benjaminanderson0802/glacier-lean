# Proof: Apify data tools — Mississippi contractor licenses

## Acceptance check

For the uncovered Mississippi board, three live license lookups must return the recorded business names, literal board statuses, expiration dates, direct source-record URLs, and UTC timestamps. Requests are rate-limited to at least one second. Source failure returns `uncertain — please check` / `unverifiable`, and a readable empty search is a dated no-match. The Apify SDK Actor must emit the same source-backed result locally. The real Glacier daily-canary flow and its evidence screenshot are the final release checks.

## Source choice

The State of Mississippi Board of Contractors offers a logged-out public search and detail pages at <https://search.msboc.us/ConsolidatedSearch.cfm>. The public records include a board disclosure that circumstances may have changed since publication, so the Actor preserves the board's wording and tells users to verify directly. No login, CAPTCHA, proxy, paid data source, or affiliation is involved.

Washington was rejected because the Apify Store already has several Washington license Actors. The Store search found current multi-state coverage from the published lists of [Contractor License Scraper](https://apify.com/ledgerfield_data/contractor-license-scraper) and [US Contractor License Scraper](https://apify.com/avant_technologies/contractor-license-scraper); Mississippi is absent from their listed state coverage. This is a point-in-time Store search, not a guarantee no new competitor will appear.

## Local live-source tests

Command:

```sh
cd ventures/apify-tools
/home/glacier/w/glacier-lean/.venv/bin/python -m unittest discover -s tests -v
```

Result: **7 tests passed**. Checks include the three live license canaries, a live name lookup, rate-limit timing, invalid search input, readable no-match handling, source outage classification, and mismatch-to-maintenance behavior.

| License | Business name | Literal status | Expiration | Result |
| --- | --- | --- | --- | --- |
| `22649` | `10TENCONSTRUCTION, LLC` | `Licensed` | `2027-05-07` | match |
| `18583` | `1ST CHOICE CONSTRUCTION SERVICES, LLC` | `Licensed` | `2027-03-18` | match |
| `21881` | `3H CONSTRUCTION LLC` | `Licensed` | `2027-10-27` | match |

The exact live results, source URLs, UTC timestamps, and health summary are saved in [live-canaries.json](/home/glacier/w/workers/gf-V-APIFY/evidence/ventures/apify-tools/live-canaries.json).

## Local Apify Actor run

Command: from `ventures/apify-tools`, write `{"license_number":"22649"}` to `storage/key_value_stores/default/INPUT.json`, then run:

```sh
/home/glacier/w/glacier-lean/.venv/bin/python -m src
```

Result: exit code `0`; Apify SDK `4.1.0`; output dataset record matched `10TENCONSTRUCTION, LLC`, literal status `Licensed`, and expiration `2027-05-07`. Saved as [local-actor-output.json](/home/glacier/w/workers/gf-V-APIFY/evidence/ventures/apify-tools/local-actor-output.json). No charge event was enabled in the local run.

## Glacier dry-run

Pending: install the two flows with `ventures/install_all.py --only apify-tools`, run `apify-ms-license-daily-canary` against a real Glacier backend, and save the verified run JSON and screen capture under `evidence/ventures/apify-tools/`.

## Owner steps

1. Set up the Apify developer account and payout details through the link in the Actor README.
2. From the repository root, run `cd ventures/apify-tools && npm exec --yes --package=apify-cli@1.10.0 -- apify login && npm exec --yes --package=apify-cli@1.10.0 -- apify push`.
3. Review the listing and publish the first Actor in Apify Console at `$0.02` per lookup, with platform usage included, a `$2.00` user run limit, and the automatic `apify-default-dataset-item` event disabled.

No account was created, credentials or payout details were entered, money was spent, or Actor published. The independent second-engine review and the PH12 phase audit remain pending.
