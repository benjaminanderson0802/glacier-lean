---
id: claim-ph12-22-heavy-test-lock
filed_by: Codex
run_id: local-card-gf-I1
node_id: integration-test-board
checkpoint: PH12.22
kind: environment
summary: Shared heavy-test lock prevented the I1 release checks from starting within the 15-minute cloud-worker backstop.
evidence: ventures/AUDIT-wave1.md; `lslocks -o PID,TYPE,MODE,COMMAND,PATH` showed PID 4283 holding `/tmp/glacier-heavy.lock` for `cd glacier/backend && ... python -m pytest -q tests`, with its pytest process waiting on Git cat-file children; the I1 filer release check had waited 15m08s.
attempts_made: 1 queued attempt, canceled after the time backstop; no test failure was observed.
status: filed
assigned_to: fixer
resolution: ""
resolution_evidence: ""
---

The shared sandbox serializes PH12 work through `/tmp/glacier-heavy.lock`. I1 queued the customer/connector and filer/mail release checks; customer and connector tests completed, but the filer step had waited 15m08s without acquiring the lock. At that time a different worker's full backend suite held the exclusive lock, and its pytest process had Git `cat-file` children sleeping for several minutes. Other backend/UI jobs were also queued. I canceled only I1's own waiting shell after the project's 15-minute cloud-worker time backstop. No other worker process was stopped. Resume the remaining release checks when the shared lock is free.
