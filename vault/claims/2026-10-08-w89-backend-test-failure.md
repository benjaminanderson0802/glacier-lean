---
id: CLM-2026-10-08-W89-BACKEND-TEST-FAILURE
filed_by: W89-declutter-shell
run_id: null
node_id: null
checkpoint: PH1.5
kind: bug
summary: Full backend suite did not send the expected alert for a failing nested flow
evidence: "bash ~/tools/suite.sh; tests/test_core.py::test_failed_run_sends_exactly_one_alert failed with got=[], suite summary: 1 failed, 597 passed, 1 skipped, 4 warnings in 520.75s"
attempts_made: 1
status: filed
assigned_to: null
resolution: null
resolution_evidence: null
---

The required backend suite completed, but `tests/test_core.py::test_failed_run_sends_exactly_one_alert` failed: the nested flow finished as failed, but the test alert receiver got no request. The full result was 1 failed, 597 passed, 1 skipped, 4 warnings in 520.75 seconds. This is outside the W89 screen and Tauri paths, so I did not inspect or change the backend implementation or its check. A backend owner should reproduce and triage it before closing this claim.
