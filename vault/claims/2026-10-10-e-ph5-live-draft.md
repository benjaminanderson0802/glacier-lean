---
id: CLM-2026-10-10-E-PH5-LIVE-DRAFT
filed_by: E-PH5
run_id: null
node_id: null
checkpoint: PH5.1
kind: bug
summary: Live Codex interview succeeds but spec drafting remains unverified after bounded retry
evidence: evidence/E-PH5/live-draft.json
attempts_made: 2
status: filed
assigned_to: debugger
resolution: null
resolution_evidence: null
---

The isolated real backend returned HTTP 200 for two real Codex interview turns.
Draft attempt one returned 502: requirements did not satisfy the existing EARS
validator. The generation schema and prompt were tightened to that same rule,
without weakening the validator. A fresh request after the owner's confirmation
returned 502: "The assistant could not answer" (official CLI adapter hides its
stderr). See `evidence/E-PH5/live-draft-retry.json`. No further draft retries were
made; the full model-generated interview-to-plan path remains unverified.

The schema/prompt change has unit coverage but is not claimed live-proven. The
runtime approval/worktree fixes are a separate reproducible unit of work, tested
with an explicitly reviewed small plan rather than accepting a failed draft.
