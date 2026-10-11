# B-READER-LABELS release benchmark evidence

## Drift check and acceptance

- Checkpoint: PH12.4. PH12 depends on PH5 and PH9, both recorded in progress; INDEX marks PH12 parallel-safe by owner authorization. This card makes no phase-exit claim and does not edit NORTHSTAR.
- Property and metrics: P-VERIFY; M-VERIFIED and M-FALSE-DONE.
- Existing tool choice: the existing public PDFs, manifest, reader, and benchmark; no new evaluation framework.
- Acceptance specified before evaluation: hash-matched public inputs; independently frozen field labels with page provenance; two local engines; at least 95% release agreement; existing missing-engine negative case passes. Do not change labels or reader code after observing results.

## Frozen labels

An independent evaluator who had not built the reader or FDA implementation labeled the seven local source PDFs before the benchmark ran. The evaluator recorded page-level provenance and marked empty form fields as blank and the ambiguous CPSC scalar as uncertain in `ventures/blocks/reader/samples/LABEL-PROVENANCE.md`. All seven manifest SHA-256 values match their PDFs. All schema fields are represented in the manifest.

The model route was idle before evaluation. The unchanged reader uses its deterministic label extractor and local Ollama model as separate engines; the local Ollama model in use was `granite3.3:2b`. The benchmark ran against the public fixture PDFs through the actual local reader/model path.

## Results

Command:

```sh
~/w/glacier-lean/.venv/bin/python -m ventures.blocks.reader.benchmark ventures/blocks/reader/samples/manifest.json
```

Result: **exit 1; release threshold not met.** The benchmark reported:

- Engine certainty/agreement: **9/13 fields = 69.23%** (threshold: 95%).
- Accuracy over non-`null` labels: **9/12 fields = 75.00%** (threshold: 95%).
- Field rows: 13 across seven public documents; 12 have a non-`null` expected value. The ambiguous CPSC label is excluded from value accuracy but remains in the 13-field certainty denominator.

Every known-value mismatch:

| Document / field | Frozen label | Reader output | Reader uncertainty | Page |
| --- | --- | --- | --- | ---: |
| GSA bill of lading / `bill_of_lading_number` | blank (`""`) | `B/L NUMBER` | no | 1 |
| GSA bill of lading / `shipper_name` | blank (`""`) | `SHIPPER NAME AND ADDRESS` | no | 1 |
| EPA energy bill / `monthly_usage` | `557` | `null` | yes | 1 |

Other uncertain fields were `cpsc-registry-guide.primary_product_id` (correctly labeled uncertain because the source shows three candidate rows), plus the two blank FDA Form 5067 fields (reader output `null`, marked uncertain). These three rows did not add a known-value mismatch; their uncertainty still contributes to the certainty denominator.

The result demonstrates that the reader can confidently return printed form headings as if they were field values, and that it did not extract the current energy usage. Labels and implementation were not changed after the result.

## Negative case and evidence boundary

Command:

```sh
/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/reader/tests/test_acceptance.py -k 'missing_second_engine'
```

Result: **1 passed, 2 deselected**. This exercises the existing fail-closed behavior for a missing second engine; no test file was edited.

This is real local inference and PDF extraction on public sample fixtures, not customer-data, production, or deployed-Glacier-backend evidence. No reader behavior was changed, so no backend server was started. The measured release gate remains unmet; see claim `CLM-2026-10-10-B-READER-LABELS-AGREEMENT` for the out-of-lane reader follow-up.
