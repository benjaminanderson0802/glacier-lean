---
id: CLM-2026-10-10-PH12-15-READER-CONFLICT-CONTRACT
filed_by: V-FDA
run_id: null
node_id: null
checkpoint: PH12.15
kind: bug
summary: "Shared reader disagreement test expects no value but the implementation retains the first candidate"
evidence: "`/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/reader/tests/test_acceptance.py` returned 1 failed / 2 passed. `test_schema_extraction_disagreement_is_uncertain` got `uncertain: true` and value `ABC-7`, but its assertion expects `value is None`."
attempts_made: 1
status: filed
assigned_to: B1
resolution: null
resolution_evidence: null
---

This is an imported shared-block issue outside V-FDA's lane. The venture does not
modify the reader block or its acceptance check. The reader contract/check docs
and this test should be reconciled by the B1 owner before release. The FDA flow
fails closed when a reader field is uncertain, so it does not generate a listing
ZIP from this disputed value.
