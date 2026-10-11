# Proof — Recall checker

## Status

The venture remains **blocked** because the independent fuzzy-match release review in `claim-ph12-12-recall-benchmark-engine` is still open. The FSIS API source canary passes with the same transparent `Glacier public-data client` User-Agent as the shared adapter. It returned HTTP 200 with 2,030 records. The recall-checker adapter selects one English notice per recall number (1,241 canonical records) and converts official FSIS notice URLs to HTTPS. The prior 403 was reproduced with the longer client User-Agent; no browser headers, impersonation or bypass were used.

## Official FSIS source canary

The official [FSIS Recall API documentation](https://www.fsis.usda.gov/science-data/developer-resources/recall-api) identifies `https://www.fsis.usda.gov/fsis/api/recall/v/1` as its GET JSON endpoint. The live probe also requested the official FSIS RSS and the HHS/CDC combined food-safety RSS. The API returned 2,030 records with recognized identifiers; FSIS RSS returned HTTP 200 and 10 recent notices; CDC RSS returned HTTP 200 and 20 items but no FSIS-linked item. The canary data is in `evidence/fsis-official-source-canary.json`.

The canary is deliberately conservative: only the documented JSON API can establish a complete snapshot. RSS records are partial coverage, and an unavailable API plus no FSIS-linked RSS record yields `status=unavailable`, `complete_snapshot=false`, and exit code 2. Tests cover API identifier parsing, partial RSS, and unavailable sources; they do not alter any independent acceptance checks.

## Benchmark

`bench/recall_benchmark.csv` contains 1,000 dated cases built from official NHTSA data: 500 recalled make/model/year cases from the NHTSA post-2010 recall flat file and 500 clean catalog make/model/year cases. A clean label requires no exact row in the downloaded recall file and an explicit zero-result response from NHTSA's recalls-by-vehicle API. The labels are model-year source-coverage labels, not VIN/configuration determinations; the CSV records source URLs, dates, method, and doubt for every case. Some API zero-result responses use HTTP 400 while returning `Count: 0` and an empty result list; the builder accepts only that explicit body.

The matcher was run against the live 245,855-row NHTSA snapshot, as of 2026-10-10. Results: 500 true positives, 0 false negatives, 0 false positive matches, 100% precision, and 100% recall. Every false negative: none. Of 500 clean cases, 261 were no-match and 239 stayed uncertain for review. This deterministic NHTSA vehicle slice is not an independent field study or an accuracy claim for other sources, barcodes, or individual VINs. Full case-level output is committed in `bench/results.json`; build and interpretation details are in `bench/README.md`.

Five example campaign URLs in the committed CSV were checked on 2026-10-10 using an ordinary browser User-Agent. All five official NHTSA API links returned HTTP 200. The earlier NHTSA HTML notice URLs returned HTTP 403 and were replaced with official campaign API links; check results are in `evidence/source-link-check.json`.

## Live Glacier engine runs

The prior three recall-checker flows were installed into a disposable `GLACIER_HOME` and run through the local Glacier engine. For this update, the isolated `GLACIER_HOME` contains fresh CPSC (193), NHTSA (245,855), FDA enforcement (87,586), and FSIS (1,241 canonical) snapshots, all with `status=ok` and no missing sources. The updated CLI review-packet command ran against those actual snapshots and generated exactly 50 pages:

```sh
GLACIER_HOME=/tmp/recall-checker-live-20261011 ~/w/glacier-lean/.venv/bin/python ventures/recall-checker/scripts/recall.py nightly --skip-sync --require-complete --limit-pages 50
```

The command reported 334,875 available records, no missing sources, no freshness problem, and 50 pages. The committed review packet is `evidence/first-50-pages/`; its run and per-source timestamps are in `evidence/first-50-pages-run.json`. No owner review or public hosting is claimed yet.

- Inventory batch: run `d03998161ce1`, status `done`. The synthetic sample inventory passed through input and result approvals; the output marks the item **uncertain — please check** because FSIS is missing. Evidence: `evidence/live-batch-run.json`, `evidence/live-batch-run.log`, and `evidence/live-batch-output.csv`. The first run, `fc6f85da9fe2`, exposed a missing approval edge and is retained with its evidence; the flow edge was fixed and the successful run repeated.
- First-page review: run `86d0aa9abb0d`, status `done` via the feed-blocked branch. It observed the incomplete feed set, generated zero pages, and recorded the blocking note. Evidence: `evidence/live-first-pages-run.json` and `evidence/live-first-pages-run.log`.
- Nightly refresh: run `7763a4301764`, final status `failed` because refresh exited 2 after the FSIS 403, including its single configured retry. The flow recorded the source alert and generated zero pages. Evidence: `evidence/live-nightly-run.json` and `evidence/live-nightly-run.log`.

The failed nightly status is retained as observed; the fail-closed behavior is the intended release safety result, not a successful refresh. A current and alert-free snapshot for every configured source is still required before public page generation.

## Checks

Commands run from the repository root with `/home/glacier/w/glacier-lean/.venv/bin/python`:

```sh
/home/glacier/w/glacier-lean/.venv/bin/python -m pytest ventures/recall-checker -q
/home/glacier/w/glacier-lean/.venv/bin/python -m pytest ventures/tests -q
/home/glacier/w/glacier-lean/.venv/bin/python ventures/install_all.py --only recall-checker --dry-run
GLACIER_HOME=/tmp/glacier-recall-benchmark-home /home/glacier/w/glacier-lean/.venv/bin/python ventures/recall-checker/bench/run_benchmark.py --output ventures/recall-checker/bench/results.json --as-of 2026-10-10
```

Latest test outcomes: recall-checker suite **27 passed**; `ventures/tests` **24 passed, 2 subtests passed**. The first-page CLI check generated 50 pages from fresh, alert-free snapshots of all four sources. No acceptance checks or `ACCEPTANCE.md` files were changed.

## Remaining gates

- Owner: review the committed first 50 pages in `evidence/first-50-pages/` and record corrections. Public hosting and marketplace submission stay gated on release verification.
- Non-owner: complete or formally resolve the independent local-model/second-engine fuzzy-match release review tracked by `claim-ph12-12-recall-benchmark-engine`; the claim cites `ventures/recall_checker.py` as outside this card's path list. Borderline results remain uncertain.
- Owner: after the verification gate clears, choose a public host and publish the prepared Apify and Chrome Web Store listings. Exact steps are in `OWNER-STEPS.md`.
