# Recall benchmark release-set evaluation

- Label freeze commit: `7146c5a7` (2026-10-11).
- Frozen labels: 500 NHTSA recalled make/model/year items and 500 synthetic clean inventory negatives.
- Dataset SHA-256: `ed7a535affa39817c39d106d4dca5f8e4f6e16e8d9d8a47e7e9832317a958ba4` (matches `release-set-manifest.json`).
- NHTSA source archive SHA-256: `252e3fa6479744a3a15386f47e6969507be2f4b06dcc9e5bf86a5a1cbc720d28`.
- Checker snapshot: 245,855 NHTSA recall rows synced into disposable `GLACIER_HOME=/tmp/glacier-recall-release-2026-10-11`.
- Unchanged command, run after the label commit: `GLACIER_HOME=/tmp/glacier-recall-release-2026-10-11 /home/glacier/w/glacier-lean/.venv/bin/python ventures/recall-checker/bench/run_benchmark.py --output evidence/backlog2/C-RECALL-BENCHMARK-TESTER/release-benchmark-results.json --as-of 2026-10-11`.

## Results

| Measure | Result | Denominator |
|---|---:|---:|
| Recalled items matched | 500 | 500 |
| False negatives (including uncertain) | 0 | 500 |
| False no-match | 0 | 500 |
| False no-match rate | 0.0% | 500 |
| Clean items returned no-match | 0 | 500 |
| Clean items returned uncertain | 500 | 500 |
| Clean items incorrectly matched | 0 | 500 |

The false no-match result meets the 1% threshold for this frozen NHTSA model-year set. All 500 synthetic clean rows returned `uncertain — please check`, so this run does not demonstrate definitive no-match handling for synthetic negatives.

## Separate borderline second-engine check

Not run: this card is data-only and the current matcher has no implemented second-engine route. That gap remains tracked by `claim-ph12-12-recall-benchmark-engine`; this benchmark result is not evidence for that route.

This is a deterministic source-coverage benchmark, not a field accuracy estimate. It does not measure CPSC, FDA, FSIS, barcodes, individual VINs, or real-world clean products. Full case-level output is in `release-benchmark-results.json`; source IDs, dates, expected outcomes, source terms, and label method are in `release-set-manifest.json` and the frozen CSV.
