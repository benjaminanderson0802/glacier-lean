---
id: CLM-2026-10-10-E-PH5-SPEC-EDITS
filed_by: E-PH5
run_id: null
node_id: null
checkpoint: PH5.2
kind: bug
summary: Build's edited spec and goal are not passed into the planner
evidence: glacier/web/src/screens/BuildTeams.tsx
attempts_made: 0
status: filed
assigned_to: integrator
resolution: null
resolution_evidence: null
---

Read-only trace: BuildTeams edits `vision` and `spec` in local state. Approve spec
calls `teamsApi.spec(spec)` and then `teamsApi.plan(visionPath, engine)`. The backend
`POST /api/build/spec` only validates and echoes the spec; it saves no version and
receives no Vision path. `POST /api/build/plan` reads the original draft Vision note.
Thus edited requirements/checks are discarded before planning; edited goal is never
sent at all. The plan can also replace the approved spec with model-generated text.

Coordinated screen/API work is needed to persist the reviewed goal and spec together
and make the planner reference that exact approved version. The E-PH5 card is backend
only; do not patch the parallel UI worker's BuildTeams.tsx or the mock from this lane.
Existing acceptance files remain tester-owned. This gap prevents claiming the complete
reviewed interview → plan path as done. No model calls or repair attempts spent here.
