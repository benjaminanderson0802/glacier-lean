---
id: CLM-2026-10-10-E-PH1-BACKEND-VERIFICATION-LOAD
filed_by: E-PH1
run_id: null
node_id: null
checkpoint: PH1.2
kind: environment
summary: Shared sandbox load prevents reliable real-backend startup verification
evidence: "evidence/E-PH1/live-runtime.log; evidence/E-PH1/baseline.log; evidence/E-PH1/backend-full.log"
attempts_made: 2
status: filed
assigned_to: fixer
resolution: null
resolution_evidence: null
---

The E-PH1 standalone live probe did not reach the API: the existing Server
helper's 60-second startup deadline expired during fresh DBOS SQLite migrations.
The trace and server output are preserved in live-runtime.log; the JSON contains
only the probe home/mode because no flow could be submitted. This is not live
success evidence for the new behavior. At inspection, /proc/loadavg reported
56.68 / 31.40 / 14.78, with multiple other cards' test and browser processes
running. No other worker's process was stopped, and no test timeout was changed.

The relevant existing suite is allowed to finish. A full-suite command was
submitted behind the shared lock, with other cards already queued ahead of it.
See the final evidence report for outcomes. Search of existing claims found
CLM-2026-10-10-PH12-22-HEAVY-TEST-LOCK, which documents the same shared-capacity
constraint and parks queued work at the escalation backstop. The fix is sandbox
test coordination, not a new dependency or a weaker acceptance test.

The full-suite request was parked after more than 15 minutes waiting for the
lock. Before cancelling its waiting `flock` process, `/proc` confirmed it had
no child process: no pytest run was interrupted. `backend-full.log` records
that it did not run. The already-running relevant suite was left to complete.

E-PH1 made a second fresh full-suite request on 2026-10-10 after the sandbox
became idle. It again waited behind another worker's full suite and a queued PH3
suite. At 15 minutes, process inspection confirmed the E-PH1 `flock` had no pytest
child; only that request was stopped. No other process was interrupted. The
focused PH1 backend suite passed independently (59 passed, 2:02); see the card's
focused test output and the committed regression-before/after logs.
