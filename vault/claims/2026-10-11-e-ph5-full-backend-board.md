---
id: CLM-2026-10-11-E-PH5-FULL-BACKEND-BOARD
filed_by: E-PH5
run_id: null
node_id: null
checkpoint: PH5
kind: bug
summary: Full backend board has seven failures outside the PH5 team lane
evidence: evidence/E-PH5/backend-full-final.log
attempts_made: 1
status: filed
assigned_to: debugger
resolution: null
resolution_evidence: null
---

The serial full backend board completed in 18m23s with 833 passed, 1 skipped, and
7 failed. Failures are outside this card's backend team execution scope:

- Three installable-template runtime cases failed because email-trigger/secret
  prerequisites were unavailable or the local AI answer was not valid JSON.
- Three Home summary tests reported unexpected pre-existing `need_you` counts
  (35, 38, and missing `run_id`).
- The persisted-schedule restart test observed no second run.

Exact traces are in the evidence log. Cause is not established; no tests were edited
or weakened. Route to the backend owners for triage and clean reproduction.
