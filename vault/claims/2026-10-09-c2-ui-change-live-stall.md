---
id: CLM-2026-10-09-C2-UI-CHANGE-LIVE-STALL
filed_by: C2
run_id: null
node_id: null
checkpoint: PH5.3
kind: bug
summary: Live Codex UI-change proposal stalls after request
evidence: "The first real Build chat request for 'make the needs-you text bold' returned a diff rejected by the 80,000-character validator; the schema did not declare the limit. After adding the limit and a focused-diff instruction, a fresh real-backend Codex request recorded assistant.model_call but produced no proposal or terminal event within 180 seconds. No Codex child process was visible while that request remained pending."
attempts_made: 2
status: filed
assigned_to: null
resolution: null
resolution_evidence: null
---

## Attempts

1. On the real Codex route, requested a focused `needs-you` bolding change. The model response exceeded `ui_change.MAX_DIFF_CHARS`, which was not represented in the structured response schema. `ui_change.propose` rejected the diff and the chat stream emitted no proposal card.
2. Added `minLength` and `maxLength` to the schema and constrained the prompt to a small, focused diff. Repeated the request in a fresh conversation. The audit database recorded `assistant.model_call` on route `codex`, but the browser received no review card within 180 seconds. The request process showed no visible Codex child process; I stopped without a third attempt.

## Remaining proof

The proposal was not approved or applied, and no branch checks ran. Investigate the stalled Codex structured-output call from a clean environment, then repeat the real UI proposal, approval, and unmerged branch checks. The schema-size correction remains in this card's working tree and has a focused backend test.
