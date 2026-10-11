---
id: CLM-2026-10-11-C-FLOW-ASSET-STAGING-PREREQUISITE
filed_by: codex
run_id: ""
node_id: prepare_packet / prepare_draft
checkpoint: PH12.22
kind: bug
summary: C-FLOW-ASSET-STAGING-TESTER cannot begin its clean-install real-backend acceptance run because the required staging integration is not present in the base checkout.
evidence: evidence/backlog2/C-FLOW-ASSET-STAGING-TESTER/preflight.md
attempts_made: 0
status: filed
assigned_to: integrator
resolution: ""
resolution_evidence: ""
---

The tester card explicitly starts after C-FLOW-ASSET-STAGING integrates. At preflight, `origin/glacier-final`, `card/gf-C-FLOW-ASSET-STAGING`, and `card/gf-C-FLOW-ASSET-STAGING-TESTER` all pointed to `27abb8c41a0fb140b66e583da8a1876f0eb2b2a5`, and the implementation worktree was clean at the same commit.

The current installer copies venture scripts into flow workspaces, but `_runtime_flow` still maps the flows' `{repo}` working directory to the absolute checkout root. The property-tax and carpenter flows therefore do not yet satisfy the requested staged-asset path. This is an out-of-lane integration prerequisite, so no live run was attempted. Once integrated, the tester can resume with a fresh disposable Glacier home.
