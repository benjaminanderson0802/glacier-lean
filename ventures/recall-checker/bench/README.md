# Recall benchmark

This committed baseline contains 500 recalled-candidate and 500 clean vehicle model-year cases. It is a NHTSA vehicle-source benchmark, not a general accuracy estimate for CPSC, FDA, FSIS, barcodes, or individual VINs.

## Sources and labels

- Recalled cases come from NHTSA's [official post-2010 recall flat file](https://static.nhtsa.gov/odi/ffdd/rcl/FLAT_RCL_POST_2010.zip). A case is a make/model/year row with a campaign number. `source_url` links to the official [NHTSA campaign API](https://api.nhtsa.gov/recalls/campaignNumber?campaignNumber=14V180000); `catalog_url` links to the flat file. `source_date` is the campaign report date. A five-link sample of campaign API URLs returned HTTP 200 on 2026-10-10; see `../evidence/source-link-check.json`.
- Clean cases are real make/model/year entries from NHTSA's [vPIC vehicle catalog](https://vpic.nhtsa.dot.gov/api/vehicles). Each candidate has no exact make/model/year row in the downloaded recall flat file and a zero-record result from NHTSA's [recalls-by-vehicle API](https://www.nhtsa.gov/nhtsa-datasets-and-apis). `source_url` is the exact API query; `catalog_url` is the exact vPIC model-list query. The source check date is `2026-10-10`.
- The NHTSA endpoint returns an empty JSON payload with `Count: 0` and `results: []` for no-record cases; some no-record requests use HTTP 400 with that same empty-result body. The dataset builder accepts only those explicit zero-result responses.
- A recalled case means a current NHTSA campaign row identifies that model-year as affected. It is not a VIN/configuration determination. The clean label means no campaign row for that model-year was found in the current source snapshot; new notices and VIN-specific applicability can change that result. Both limits are carried in each CSV row's `doubt` field.

## Rebuild and run

Use the repository interpreter. First sync the official NHTSA flat file into a disposable Glacier home, then build and evaluate the CSV:

```sh
GLACIER_HOME=/tmp/recall-benchmark /home/glacier/w/glacier-lean/.venv/bin/python -m ventures.blocks.feeds.cli sync nhtsa_recalls
GLACIER_HOME=/tmp/recall-benchmark /home/glacier/w/glacier-lean/.venv/bin/python ventures/recall-checker/bench/build_dataset.py --date 2026-10-10
GLACIER_HOME=/tmp/recall-benchmark /home/glacier/w/glacier-lean/.venv/bin/python ventures/recall-checker/bench/run_benchmark.py --output ventures/recall-checker/bench/results.json --as-of 2026-10-10
```

`results.json` stores the case-level outputs, precision, recall, every false negative, every false positive, and uncertain cases. A model/year query with a near model-family result remains `uncertain — please check` rather than being promoted to a match. No independent local-model/second-engine review has been completed yet; this is the assigned matcher plus source labels, not independent validation.

## Run evidence

The 2026-10-10 live snapshot contained 245,855 NHTSA rows. Benchmark result: 500 true positives, 0 false negatives, 0 false positive matches; precision 100%, recall 100%, false no-match rate on recalled cases 0%, within the 1% gate. Among the 500 clean cases, 261 returned no-match and 239 stayed uncertain because a same-brand/model-family campaign needed review. This is a deterministic source-coverage baseline, not an independent field study or a cross-source product benchmark.
