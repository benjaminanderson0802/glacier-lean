# Proof — Recall checker

## Status

The venture remains **blocked**. The source-coverage benchmark and real local Glacier runs are complete, but FSIS still returns HTTP 403 through the shared feed adapter. The live nightly flow recorded the alert and generated no pages. The separate second-engine review for fuzzy matches also remains open in `claim-ph12-12-recall-benchmark-engine`. Neither blocker is an owner-only action.

## Benchmark

`bench/recall_benchmark.csv` contains 1,000 dated cases built from official NHTSA data: 500 recalled make/model/year cases from the NHTSA post-2010 recall flat file and 500 clean catalog make/model/year cases. A clean label requires no exact row in the downloaded recall file and an explicit zero-result response from NHTSA's recalls-by-vehicle API. The labels are model-year source-coverage labels, not VIN/configuration determinations; the CSV records source URLs, dates, method, and doubt for every case. Some API zero-result responses use HTTP 400 while returning `Count: 0` and an empty result list; the builder accepts only that explicit body.

The matcher was run against the live 245,855-row NHTSA snapshot, as of 2026-10-10. Results: 500 true positives, 0 false negatives, 0 false positive matches, 100% precision, and 100% recall. Every false negative: none. Of 500 clean cases, 261 were no-match and 239 stayed uncertain for review. This deterministic NHTSA vehicle slice is not an independent field study or an accuracy claim for other sources, barcodes, or individual VINs. Full case-level output is committed in `bench/results.json`; build and interpretation details are in `bench/README.md`.

Five example campaign URLs in the committed CSV were checked on 2026-10-10 using an ordinary browser User-Agent. All five official NHTSA API links returned HTTP 200. The earlier NHTSA HTML notice URLs returned HTTP 403 and were replaced with official campaign API links; check results are in `evidence/source-link-check.json`.

## Live Glacier engine runs

The three recall-checker flows were installed into a disposable `GLACIER_HOME` and run through the local Glacier engine. Source snapshots refreshed in that home: CPSC 10,047 rows, NHTSA 245,855 rows, and FDA enforcement 87,586 rows. FSIS returned HTTP 403, with zero rows. No production account or external publication was used.

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

Latest test outcomes: recall-checker suite **20 passed**; venture suite **21 passed**; installer dry-run validates all three flows. Benchmark output reports the counts above and `false_negatives=[]`. No acceptance checks or `ACCEPTANCE.md` files were changed.

## Remaining gates

- Non-owner: resolve the FSIS 403 through the shared feed-owner lane/claim `CLM-2026-10-10-B2-FSIS-API-403`, then refresh and rerun the engine flows. Do not bypass the source restriction or generate public pages from an incomplete source set.
- Non-owner: complete the independent local-model/second-engine fuzzy-match review tracked by `claim-ph12-12-recall-benchmark-engine`.
- Owner: review the first 50 generated pages and choose a public host. Account, pricing, billing, and marketplace publication steps remain described in `README.md`.
