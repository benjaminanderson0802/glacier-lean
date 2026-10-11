---
id: CLM-2026-10-09-C2-IMPORTED-CODEX-SEND
filed_by: C2
run_id: null
node_id: null
checkpoint: PH6.2
kind: bug
summary: Sending to one imported Codex Messenger session returns 502
evidence: "On the real backend, the imported Codex thread reported can_send=true, but POST /api/messages/threads/codex%3A01a122f5-d103-7080-9716-e20fd2e05073 returned HTTP 502. A fresh Codex Messenger thread subsequently replied successfully."
attempts_made: 1
status: closed
assigned_to: null
resolution: "The reported session id is valid and resumable: the local official Codex CLI and a disposable real backend both resumed it successfully. The 502 came from the route treating any non-zero CLI resume as a generic upstream failure; session corruption and id format problems were not reproduced. Codex resume now uses --all to avoid depending on the backend working directory. If an official CLI rejects a session, Glacier marks it read-only and shows a plain reason instead of returning 502."
resolution_evidence: "glacier/backend/tests/test_messages.py::test_codex_and_claude_resume_use_configured_fake_commands; glacier/backend/tests/test_messages.py::test_a_session_rejected_by_codex_becomes_read_only; live backend POST /api/messages/threads/codex%3A01a122f5-d103-7080-9716-e20fd2e05073 returned HTTP 200 with the expected reply; glacier/web/e2e/messenger.spec.mjs PASS; glacier/web/e2e/live_real_backend.spec.mjs PASS; full backend suite 771 passed, 1 skipped"
---

The UI indicated that the imported Codex session accepted messages, but its send endpoint returned 502. The fresh Codex thread path worked, so the session-specific failure was not repeated. Determine whether the imported transcript is malformed, the CLI resume command rejected it, or another route issue is responsible; then either disable sending for unsupported sessions or make their send path return a useful error.
