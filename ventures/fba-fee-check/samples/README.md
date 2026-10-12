# Sample provenance

`sample-fee-digest.csv` was generated on 2026-10-10 from the synthetic seller-shaped files in `tests/fixtures/settlement-v2.tsv` and `tests/fixtures/expected-fees.csv`. It is not generated from live Amazon or seller data. Amazon's Settlement Report V2 is seller-specific and requires the seller's own Seller Central report; no keyless official dataset matching these transaction rows was available for a real-data sample.

Column names and flat-file shape follow Amazon's official [Settlement Reports — Flat File V2 documentation](https://developer-docs.amazon.com/sp-api/docs/report-type-values-settlement#flat-file-v2-settlement-report). Fee amounts and SKUs in the fixture are illustrative only.
