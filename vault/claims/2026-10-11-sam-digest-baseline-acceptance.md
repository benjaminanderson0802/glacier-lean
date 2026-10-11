---
id: CLM-2026-10-11-SAM-DIGEST-BASELINE-ACCEPTANCE
filed_by: B-SAM-COLLECT
run_id: null
node_id: null
checkpoint: PH12.5
kind: bug
summary: Existing SAM digest acceptance checks fail on the integrated baseline
evidence: "Before collector implementation, ~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/sam-amendment-alerts/tests reported 6 failed, 13 passed, 1 skipped. Failures are all in read-only tests/acceptance/test_sam_amendment_alerts.py and concern supplied uiLink preservation, incomplete/undated/malformed snapshots, and missing-deadline uncertainty. The collector does not touch digest.py or these checks."
attempts_made: 1
status: filed
assigned_to: sam-digest owner/integrator
resolution: ""
resolution_evidence: ""
---

## Reproduction and scope

The required SAM pilot suite was run before adding collector code:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/sam-amendment-alerts/tests
```

Result: **6 failed, 13 passed, 1 skipped**. All failures are in the existing read-only digest acceptance file. They reproduce existing behavior in `scripts/digest.py`: events use the API self link instead of `uiLink`; incomplete, missing-retrieval, and malformed snapshot metadata can still produce a confident result; and a new notice with no response deadline does not carry explicit uncertainty.

These paths are outside B-SAM-COLLECT's allowed edit list and belong to the separate SAM digest lane. No repair was attempted. Collector work may be evaluated with its own fixture tests, but the required full venture suite remains red until the digest lane resolves these failures.
