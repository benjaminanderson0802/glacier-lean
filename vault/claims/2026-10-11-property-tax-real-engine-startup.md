---
id: CLM-2026-10-11-PROPERTY-TAX-REAL-ENGINE-STARTUP
filed_by: Codex
run_id: null
node_id: null
checkpoint: PH12.17
kind: bug
summary: Property-tax proof runner stopped after an immediate connection refusal before polling for backend readiness
evidence: ventures/property-tax/evidence/glacier-live-backend-2026-10-11.log; ventures/property-tax/evidence/glacier-live-run-2026-10-11.json
attempts_made: 2
status: filed
assigned_to: debugger
resolution: null
resolution_evidence: null
---

The flow edge defect is fixed in this card, and the new unit regression checks that the approval edge routes `yes` to `prepare_packet`. A fresh proof attempt is still required before PH12.17 can be considered ready.

Attempt 1 stopped before backend launch because sample normalization accidentally used the default `GLACIER_HOME`; it compared the sample schema against an unrelated existing schema. The attempt was discarded and did not write venture data.

Attempt 2 used a new temporary home and set `GLACIER_HOME` before normalization. It staged all 50 sample records with no schema alerts, then launched `uvicorn app:app` in a child process. The proof runner made one API request immediately, without polling or catching the expected startup connection refusal; that request failed with `URLError: <urlopen error [Errno 111] Connection refused>`, and the `finally` block terminated the child. The empty backend log therefore does not show whether startup would have succeeded. Do not claim the engine run or protected acceptance passed.

No further attempts were made after the two attempts. A fresh proof runner must poll readiness with a bounded timeout and preserve the child process logs before installing the flow and approving its gates. Expected proof: installed edge label `yes`, `prepare_packet` done, packet output present, protected command check passed, and no external effects. The public sample contains parcel metadata only; missing customer notice and sale evidence must stay uncertain.
