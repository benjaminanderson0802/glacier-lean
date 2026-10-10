---
id: CLM-2026-10-09-C2-IMPORTED-CODEX-SEND
filed_by: C2
run_id: null
node_id: null
checkpoint: PH5.1
kind: bug
summary: Sending to one imported Codex Messenger session returns 502
evidence: "On the real backend, the imported Codex thread reported can_send=true, but POST /api/messages/threads/codex%3A01a122f5-d103-7080-9716-e20fd2e05073 returned HTTP 502. A fresh Codex Messenger thread subsequently replied successfully."
attempts_made: 1
status: filed
assigned_to: null
resolution: null
resolution_evidence: null
---

The UI indicated that the imported Codex session accepted messages, but its send endpoint returned 502. The fresh Codex thread path worked, so the session-specific failure was not repeated. Determine whether the imported transcript is malformed, the CLI resume command rejected it, or another route issue is responsible; then either disable sending for unsupported sessions or make their send path return a useful error.
