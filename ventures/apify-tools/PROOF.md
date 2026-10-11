# Proof: Apify data tools — Mississippi and Louisiana contractor licenses

## Acceptance check

For each included board, three live license lookups must return the recorded business names, literal board statuses, expiration dates, direct source-record URLs, and UTC timestamps. Requests are rate-limited to at least one second. Source failure returns `uncertain — please check` / `unverifiable`, and a readable empty search is a dated no-match. Each Apify SDK Actor must emit the same source-backed result locally. The real Glacier daily-canary flow is a release check for each board; Mississippi's existing run and screenshot are recorded above, and Louisiana's verified real-backend run is saved in its package evidence.

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

The real Glacier session started under `flock /tmp/glacier-heavy.lock bash -lc 'cd glacier/web && npm run live'` printed API `http://127.0.0.1:38841`, UI `http://127.0.0.1:39729`, and disposable home `/tmp/glacier-live-sWSWHp`. Commands:

```sh
GLACIER_HOME=/tmp/glacier-live-sWSWHp GLACIER_API=http://127.0.0.1:38841/api \
  /home/glacier/w/glacier-lean/.venv/bin/python ventures/install_all.py --only apify-tools
POST http://127.0.0.1:38841/api/environments/apify-ms-license-daily-canary/run
```

The POST returned `{"run_id":"26c2afcecb34"}`. The run finished `done`, `verified: true`; nodes `daily`, `canaries`, `canary_result`, and `status_note` all finished. The acceptance command passed; the source canary state was `healthy`, `failed_license_numbers: []`, and all three recorded records matched. Run JSON, live canary JSON, and the note written into the disposable Glacier vault are saved in [glacier-live-run.json](/home/glacier/w/workers/gf-V-APIFY/evidence/ventures/apify-tools/glacier-live-run.json), [glacier-live-canaries.json](/home/glacier/w/workers/gf-V-APIFY/evidence/ventures/apify-tools/glacier-live-canaries.json), and [glacier-live-note.md](/home/glacier/w/workers/gf-V-APIFY/evidence/ventures/apify-tools/glacier-live-note.md). [glacier-live.png](/home/glacier/w/workers/gf-V-APIFY/evidence/ventures/apify-tools/glacier-live.png) captures the real screen showing the completed run and passed checks.

## Owner steps

1. Set up the Apify developer and payout account, log in with the pinned CLI, and upload both Actor folders using the commands in the [venture manifest](venture.json).
2. Review and publish each listing separately. Each of the first three distinct Actor publications needs a separate Glacier approval and different-engine review; confirm the event price, platform usage, run limit, and disabled automatic `apify-default-dataset-item` event before publishing it yourself.

No account was created, credentials or payout details were entered, money was spent, or Actor published. The independent second-engine review and the PH12 phase audit remain pending.

## Louisiana second board: live probe and draft Actor

The candidate live probes were made before implementing the adapter on 2026-10-11 UTC. The Alabama Home Builders Licensure Board homepage was reachable, but its linked GLSuite license portal returned HTTP 403. Alabama's Electrical Contractor Board homepage was reachable, but the page exposed a renewal portal rather than a clear public license search. Georgia's Secretary of State verification page returned HTTP 403. The official Louisiana LSLBC contractor-search page and its linked search portal both returned HTTP 200 without an account. The portal exposes separate keyless company-name and license-number searches. A live POST by license number and a follow-up public detail request both returned records without credentials.

Louisiana was selected for the clearest working keyless search and broad commercial and residential contractor scope. The source returned as many as 1,500 rows for broad company-name searches; this supports a sizeable searchable record set. No comparative paid demand or customer-volume study was run, so this is a practical scope/accessibility choice rather than a measured market-demand ranking.

The live canary values, official record URLs, and UTC probe times are in [`apify-tools-louisiana/tests/canaries.json`](apify-tools-louisiana/tests/canaries.json). The daily live canary output is saved in [`apify-tools-louisiana/evidence/live-canary-run.json`](apify-tools-louisiana/evidence/live-canary-run.json). `pytest ventures/apify-tools-louisiana -q` returned **9 passed, 3 live canary subtests passed**. Coverage includes all three source records, a name search, readable no-match, malformed search/schema and outage classification, incomplete records, search validation, request spacing, canary mismatch handling, and Actor input-schema shape. The canaries matched `CL.00001` (BROWN & ROOT INDUSTRIAL SERVICES, LLC, `Active`, expires `2027-07-31`), `CL.68755` (09 Construction Services, LLC, `Active`, expires `2029-07-18`), and `RL.883684` (BROWN & ROOT INDUSTRIAL SERVICES, LLC, `Active`, expires `2027-09-12`).

The standalone Actor used the shared `src/actor_template.py` lifecycle and emitted the live `CL.68755` record with the expected status, expiration date, and official detail URL. Its output is saved in [`apify-tools-louisiana/evidence/local-actor-output.json`](apify-tools-louisiana/evidence/local-actor-output.json). Its pinned `requirements.txt` is byte-identical to Mississippi's. The Apify input schema has no top-level editor, marks its array input with `editor: json`, and defines no nested array item schema. `ventures/tests/test_install_all.py` now derives Apify flow expectations from its manifest, which declares four flows across the two boards.

The Louisiana Actor is a **review draft**. Its distinct-engine code and Store-listing review by OpenCode `opencode/nemotron-3.5-lightning-free` found no blocking findings; the review is recorded in [`apify-tools-louisiana/REVIEW.md`](apify-tools-louisiana/REVIEW.md). Its Louisiana daily flow was installed through the real Glacier API and completed `done`, `verified: true` (final run `5a0844b62ec4`); the response is saved in [`apify-tools-louisiana/evidence/glacier-flow-run.json`](apify-tools-louisiana/evidence/glacier-flow-run.json). The Louisiana-specific owner publication approval remains a prerequisite to publication. Account creation, payout setup, CLI login/upload, spending, and publication were not performed.
