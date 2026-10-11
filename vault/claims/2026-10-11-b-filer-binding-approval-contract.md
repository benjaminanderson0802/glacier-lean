---
id: CLM-2026-10-11-B-FILER-BINDING-APPROVAL-CONTRACT
filed_by: B-FILER-BINDING
run_id: null
node_id: ventures.blocks.filer.submit
checkpoint: PH12.7
kind: unclear_spec
summary: Filer submission cannot verify a draft-bound owner approval through the current public approval contract
evidence: >
  docs/CONTRACT.md: POST /api/runs/{run_id}/approve takes node_id and approved;
  GET /api/runs/{run_id} exposes node states/outputs but no filer authorization object.
  The local filer baseline also reproduces vault/claims/2026-10-09-ph12-7-playwright-actionability.md.
attempts_made: 0
status: filed
assigned_to: integrator
resolution: null
resolution_evidence: null
---

The card requires `submit(draft, approval_id)` to reuse Glacier's existing authority and reject invented strings. The public API defines durable approval for a particular run/node, but does not define how the filer receives or validates an approval for a specific prepared portal, customer scope, destination, and field digest. Its approval endpoint returns only `{ok: true}`; the run endpoint reports a completed node output but does not bind that approval to the filer draft. The implementation must not invent an `approval_id` encoding or trust any non-empty string as authority.

Before changing code, the required local baseline was run with the pinned module dependency installed. `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/filer/tests` produced 1 pass and 2 failures: both failures timed out waiting for the same login button to become stable. A separate two-local-origin reproduction stopped at the same prepare timeout before reaching submit. This matches the existing PH12.7 Playwright actionability claim; no further retries or workaround edits were attempted after the repeated failure.

Integrator handoff: define or identify the public approval reference that the filer can validate against the exact prepared draft and customer scope, and route the existing Playwright actionability claim to its assigned debugger. Then resume B-FILER-BINDING from a fresh context and reproduce destination swap, field edit, cross-origin navigation, and cross-customer replay before implementation. No real portal, account, filing, or customer data was used.
