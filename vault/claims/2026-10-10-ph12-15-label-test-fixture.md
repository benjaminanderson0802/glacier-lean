---
id: CLM-2026-10-10-PH12-15-LABEL-TEST-FIXTURE
filed_by: V-FDA
run_id: null
node_id: null
checkpoint: PH12.15
kind: bug
summary: "FDA listing acceptance tests cannot reach mocked reader because the label fixture path is missing"
evidence: "`/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/fda-cosmetics/tests/test_fda_cosmetics.py` first failed with FileNotFoundError for `label.pdf`; after the missing-file guard was added, rerun returned 4 failed / 3 passed because the required document was still absent, so the mock was not called and otherwise complete test records remained uncertain. `ventures/fda-cosmetics/scripts/listing_prep.py` now fails closed when the label path is absent."
attempts_made: 2
status: filed
assigned_to: null
resolution: null
resolution_evidence: null
---

The product acceptance test must provide an existing temporary label path when it
mocks `read_document`. The current test helper points to `label.pdf`, but that file
does not exist in the test process. The guard correctly leaves missing labels
uncertain; the tests need their own isolated label fixture before they can verify
successful packet generation and reader disagreement handling. No FDA or customer
records were used. The task is parked under the NORTHSTAR escalation rule.
