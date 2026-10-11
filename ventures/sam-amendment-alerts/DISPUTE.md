# Dispute: legacy empty-snapshot unit fixture

`tests/test_digest.py::test_digest_reports_no_match_with_the_source_date` supplies an empty `opportunitiesData` list with `retrieved_at` and `source_url`, but omits the documented v2 pagination fields `totalRecords`, `limit`, and `offset`. The test expects a confident no-match from a snapshot whose page coverage cannot be established. That expectation conflicts with the venture acceptance contract: empty input must be distinguishable from missing or incomplete input, and a no-match requires complete dated snapshots.

Corrected assertion: keep the no-match expectation, but make both empty snapshots valid complete v2 envelopes with `totalRecords: 0`, a positive `limit`, `offset: 0`, and their existing dated local `retrieved_at` metadata. Alternatively, if the pagination fields are intentionally absent, assert that comparison rejects the snapshots (or returns `uncertain - please check`) instead of asserting a no-match.
