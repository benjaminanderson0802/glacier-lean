# Contract: Verification and claims (frozen for wave 1; changes only through the integrator)

## Acceptance checks (defined before work starts; rule I-03)
A flow may carry `"acceptance": [Check, ...]`. A run is **verified** only if every required check passes, run by the verifier in a separate context the worker cannot change (I-04).
Check = one of:
- `{"kind": "command", "cmd": "pytest -q", "cwd": "optional", "required": true}`        exit 0 = pass
- `{"kind": "schema", "file": "out.json", "schema": {...JSON Schema...}, "required": true}`
- `{"kind": "rubric", "rubric": "plain-language criteria", "engine": "auto|local|codex", "required": true}`  judged by a different context than the worker; verdict pass/fail with reasons
- `{"kind": "human", "question": "Does the report look right?", "required": true}`          owner approves/rejects
GET /api/runs/{id} adds: `verified: true|false|null` (null = no checks or not finished), `verification: [{check, passed, evidence}]`.
Workers can never see or edit check files: checks are copied from the saved flow when the run starts and run outside the worker's folder.

## Claims (files, rule I-15)
Path: `vault/claims/YYYY-MM-DD-<slug>.md`, front matter:
`id, filed_by, run_id, node_id, checkpoint, kind (bug|environment|capability_gap|skill_gap|unclear_spec|policy), summary, attempts_made, status (filed|researching|resolved|routed|proposed|closed), assigned_to (researcher|fixer|debugger|verifier|owner), resolution, resolution_evidence`
Body sections: `## Problem`, `## Evidence`, `## Research`, `## Proposal` (only when proposed), `## Resolution`.

## Claims API (route plug-in glacier/backend/routes/claims.py) and MCP tool
- POST /api/claims {kind, summary, evidence, run_id?, node_id?, attempts_made?} -> {id, path}; MCP tool `file_claim` does the same for workers.
- GET  /api/claims?status=  -> [{id, kind, summary, status, assigned_to, updated}]
- GET  /api/claims/{id}     -> {meta, body}
- POST /api/claims/{id}/decision {action: approve|reject|research_more, option?: str} -> {status}   (owner only; for proposals)
Events: `{"type": "claim", "id", "status"}`.

## Proposal (when no free/open-source option fits, or money/policy is involved)
The `## Proposal` section lists: the problem in plain language; every free/OSS option checked and why each fails; paid/closed options with cost, license, lock-in and whether data leaves the machine; a recommendation; what happens if the owner says no.
