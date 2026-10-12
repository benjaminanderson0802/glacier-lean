---
id: CLM-2026-10-10-PH12-1-P1-MANIFEST-TEST-ISOLATION
filed_by: P1-ventures
run_id: null
node_id: null
checkpoint: PH12.1
kind: bug
summary: P1 venture test assumes the temporary home contains only its fixture manifest
evidence: "After rebasing onto the integrated PH12 base, `flock /tmp/glacier-heavy.lock bash -c 'cd glacier/backend && /home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q tests/test_ventures.py'` reported 1 failed, 5 passed. `test_ventures_reads_installed_manifest_and_today_run_state` expected `len(rows) == 1`, but startup installation correctly included the newly bundled `carpenter-goods` manifest alongside the test's `truck-dispatch` fixture (2 rows)."
attempts_made: 1
status: filed
assigned_to: null
resolution: null
resolution_evidence: null
---

The test's intended assertion is that the `truck-dispatch` manifest appears with its run state and report counts. The exact-row-count assertion no longer holds when the backend startup installer copies every bundled venture into a new Glacier home. The test is part of this card's acceptance check, so P1 did not edit it (I-04). The other five tests in `tests/test_ventures.py` passed on the integrated base.
