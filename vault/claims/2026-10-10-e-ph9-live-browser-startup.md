---
id: CLM-2026-10-10-E-PH9-LIVE-BROWSER-STARTUP
filed_by: E-PH9
run_id: null
node_id: null
checkpoint: PH9.1
kind: environment
summary: Existing real-backend browser check timed out during backend startup on the shared host
evidence: evidence/ph9/live-browser.log; evidence/ph9/mock-core.log; evidence/ph9/maintenance-queue.json
attempts_made: 0
status: filed
assigned_to: fixer
resolution: null
resolution_evidence: null
---

After the private dependency install and successful build, `node e2e/live_real_backend.spec.mjs` exited 1. Its 60-second UI readiness wait expired while the real backend was still initializing DBOS/SQLite. The log contains no completed browser assertions. Multiple other workers were running backend suites on this host; contention is a possible explanation, not a confirmed cause.

This is outside E-PH9's self-build implementation scope. The existing browser check and its timeouts were not edited, and no other worker process was stopped. The dedicated PH9 maintenance capture uses a fresh home/free port and waits for the shared suite lock before starting. The fixture-based self-build suite remains independently green. A tester/fixer should rerun the unchanged live-browser check with available host capacity before claiming browser proof.

The unchanged mock core spec also failed: it connected the events socket, then timed out clicking `data-testid="new-env"` after 30 seconds. The log is retained; no UI files were changed. The maintenance capture remained queued behind PID 397779 on the shared suite lock and had not created a backend/home/run. Its own waiting flock process (402721, no children) was cancelled after the out-of-lane project-gate failure was confirmed. No full backend suite was cancelled, and no foreign process was signalled. Current maintenance live proof remains pending.
