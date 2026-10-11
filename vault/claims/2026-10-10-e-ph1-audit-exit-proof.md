---
id: CLM-2026-10-10-E-PH1-AUDIT-EXIT-PROOF
filed_by: E-PH1
run_id: null
node_id: null
checkpoint: PH1
kind: capability_gap
summary: Runtime audit exit still needs independent coverage including interrupted effects and unavailable storage
evidence: "glacier/backend/audit_log.py: record; glacier/backend/tests/test_audit_log_resilience.py: test_unavailable_audit_store_does_not_change_runner_result; evidence/E-PH1/plan.md"
attempts_made: 0
status: filed
assigned_to: independent_tester
resolution: null
resolution_evidence: null
---

PH1 requires M-AUDIT = 100% for runtime side effects. Existing evidence measures
selected successful API effects and git-backed recovery. The recorder explicitly
drops events on unavailable audit storage, and the existing resilience test
requires a successful command to remain successful in that case. Commands are
recorded after they return, so a process crash after an external effect but before
recording can also leave a gap. Builder regression results cannot certify the
whole phase exit. No acceptance test is changed or weakened here.

E-PH1 fixes three concrete event-placement defects using the existing recorder:
retry attempts, duplicate child starts and missing scheduled starts. Further
audit durability needs a tester-defined acceptance contract for attempted versus
completed effects and crash recovery. Existing DBOS durable steps and SQLite
transactions are the available free tools; do not introduce a custom workflow
engine. Route this evidence gap to the tester/integrator; keep PH1 in progress.
