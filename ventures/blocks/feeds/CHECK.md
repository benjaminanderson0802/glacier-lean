# Government data feed release check

Release only when the following pass:

1. `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/feeds/tests` passes, including schema-change, database, canary, and daily-flow checks.
2. `~/w/glacier-lean/.venv/bin/python -m ventures.blocks.feeds.cli sync-all` runs against the ten registered source paths. Record per-source normalized row counts, published totals where available, canary status, timings and every source/format alert in this check.
3. Where a source publishes a comparable total, normalized row count is within 1% or an alert blocks release. A source that cannot be fetched or whose format has changed is not marked passing.
4. A second run with no source changes reports `changed: false` for unchanged snapshots.
5. `flows/daily_sync.json` has a daily 02:00 schedule and syncs every source in `sources.json`. Alerts route through a durable approval and note step.

Current source set: CPSC HTS flagging list, CPSC citation/testing exception codes, CPSC bulk upload template, CPSC Recalls API, NHTSA flat-file download, FDA openFDA food enforcement, FSIS Recall API, OSHA ITA establishment summary CSV, DLA DIBBS public solicitation page, and Cook County Assessor open data. No authentication, purchase, account creation, bidding, or government submission occurs.

## Live access recheck (2026-10-10)

Drift check: this work advances PH12.5, Shared block: government data feeds + deadline tracker. PH12 depends on PH5 and PH9; PH5 is still in progress, so the card was authorized to start but the checkpoint is not marked done. This serves P-LOOPS/P-VERIFY and M-VERIFIED/M-INTERVENE. Reused the existing standard-library feed adapter, SQLite snapshot cache and published Socrata API; no new dependency or service was added. Acceptance: focused feed tests pass; each registered source is live-checked; counts, elapsed time and access/format alerts are recorded; totals are compared within 1% where independently published.

Live requests used `Glacier public-data client/1.0 (+https://github.com/benjaminanderson0802/glacier-lean)` with honest JSON/RSS/CSV/HTML Accept headers, 30-second default timeouts, three attempts for transient failures, exponential waits, and a five-minute HTTP cache for responses up to 20 MB. No browser identity, consent action, login, robots bypass or terms bypass was used. Cook County's `robots.txt` declares a one-second crawl delay; the client now observes it. CPSC's `robots.txt` does not disallow the REST API or eFiling library paths queried; SaferProducts.gov and api.fda.gov returned no robots file (404). DIBBS `/robots.txt` itself redirects to the DoD notice and consent form, so it was not acknowledged. FSIS, OSHA, and NHTSA robots endpoints returned 403 and could not be read; their published data routes were requested with the descriptive client ID, and no blocked page was circumvented. Official source docs: [CPSC recalls API and data downloads](https://www.cpsc.gov/Recalls/CPSC-Recalls-Application-Program-Interface-API-Information), [FSIS JSON Recall API and RSS](https://www.fsis.usda.gov/science-data/developer-resources/recall-api), [Cook County Assessor dataset](https://datacatalog.cookcountyil.gov/Property-Taxation/Assessor-Parcel-Universe/nj4t-kc8j), [Cook County property classification codes](https://www.cookcountyassessor.com/form-document/codes-classification-property), and [DLA vendor guidance on public DIBBS RFQ records](https://www.dla.mil/Land-and-Maritime/Business/Selling/Vendor-Assistance/HQ/HQ/PublicAffairsOffice/).

The runs used a disposable `GLACIER_HOME` under `/tmp`, so they did not modify the owner's feed database. Times include source retrieval and normalization; Cook County took three resumable invocations because its per-invocation page cap is five 10,000-row pages.

| Source | Live result | Elapsed | Alerts / disposition |
| --- | ---: | ---: | --- |
| CPSC flagged HTS codes | 589 rows | 0.61 s | None. Downloaded the official October 2026 XLSX workbook's CP1/CP2 sheets. |
| CPSC citation/testing exception codes | 130 rows | 0.30 s | None. Official XLSX downloaded. |
| CPSC registry template | 1 template / header record | 0.33 s | None. Current version 3 workbook downloaded. |
| CPSC recalls REST API | 10,047 rows | 22.45 s | None. Official JSON API retrieved in five-year date windows; the API does not publish a comparable total. |
| NHTSA recalls | 245,855 rows | 150.68 s | None. Official flat-file ZIP and field dictionary both parsed. |
| FDA openFDA enforcement | 87,586 rows | 102.72 s | None. Official download catalog partitions; source total matched. |
| FSIS recalls | 0 rows | 0.34 s | HTTP 403 from documented official JSON API. Do not spoof or retry around the block. `sources.json` records the owner fallback: use the official FSIS recalls page/RSS in a normal browser or import its saved notice file. |
| OSHA ITA summaries | 0 rows | 0.22 s | HTTP 403 from the official page/download path. `sources.json` records the owner fallback to download the current Summary Data CSV in a normal browser and import it locally. |
| DLA DIBBS solicitations | 0 rows | 2.23 s | Official DoD Notice and Consent page returned. No acknowledgement was attempted. `sources.json` records the owner step to review the terms in a normal browser and download a selected public RFQ file; there is no documented bulk feed. |
| Cook County Assessor (2026, class 211 / class 2-11 apartment buildings with 2–6 units) | 149,931 rows / 149,931 filtered source rows | 83.43 s across 3 staged invocations | No source or 1% count alerts. Incremental repeat: 0 changed rows in 5.87 s, `changed: false`. Only selected parcel fields and `:updated_at` were fetched. This is a narrow initial cohort; the venture owner still needs to set target townships/classes for broader service. |

Status: CPSC, NHTSA, FDA, and the filtered Cook County path are automated and live. The Cook County result covers only the 2-11 apartment cohort and is not a full county roll; the owner must choose target townships/classes for the intended appeal service. FSIS and OSHA remain owner-download steps after HTTP 403. DIBBS remains an owner-reviewed consent/download step. These three rows are not release-passing automated feeds and should remain visible as alerts until their owner steps are completed or the official source access changes.

Focused verification: `/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/feeds/tests/test_feeds.py` — **15 passed**. `python -m json.tool ventures/blocks/feeds/sources.json` and `git diff --check` also passed. No heavy jobs were run.

Anti-pattern review: prior CHECK text documented failed live syncs without matching the published source paths. Corrected CPSC's discovery to match current official filenames, chunked the full history, and replaced the oversized county export with a scoped and incremental query. Remaining 403/consent responses are now surfaced as explicit owner steps rather than reported as successful syncs.
