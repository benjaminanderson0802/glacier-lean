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
status: resolved
assigned_to: null
resolution: "The protected FDA acceptance fixture check now passes; no acceptance file was changed in this card."
resolution_evidence: "ventures/fda-cosmetics/PROOF.md; ~/w/glacier-lean/.venv/bin/python -m pytest ventures/fda-cosmetics/tests/acceptance/test_v_fda2.py -q --runxfail (3 passed)"
---

The earlier reported missing-label fixture failure no longer reproduces: the
protected V-FDA2 acceptance suite passes in the current tree. This card did not
modify its test or fixture. No FDA or customer records were used.
