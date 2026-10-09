---
id: CLM-2026-10-09-B5-LIVE-LOG-FLAKE
filed_by: B5
run_id: null
node_id: null
checkpoint: PH1.2
kind: bug
summary: Codex live-log backend test remains load-sensitive
evidence: "Two focused attempts at a test-only process gate still failed to observe a live output line. The existing acceptance test passed alone in the audit rerun but failed during the full backend suite. No production Codex streaming assertion was weakened."
attempts_made: 2
status: filed
assigned_to: null
resolution: null
resolution_evidence: null
---

The test fake emits JSONL events while the backend flushes node output on a two-second interval. A pause inserted before a later line prevents the backend's blocking stdout iterator from reaching its flush check, so the test deadlocks waiting for output. The second focused run reproduced the same symptom after adding a delay; the live-log test change is parked under NORTHSTAR escalation. Rework the synchronization from a fresh context before changing the test again.
