---
id: CLM-PH12-20-CWD-REPO
filed_by: codex
run_id: 5d5ed16d92a4
node_id: prepare_draft
checkpoint: PH12.20
kind: bug
summary: Flow command cwd does not expand the {repo} placeholder for venture scripts.
evidence: "Real Glacier live run 5d5ed16d92a4: prepare_draft failed with [Errno 2] No such file or directory: '/tmp/carpenter-goods-live.685QDI/workspaces/carpenter-prepare-listing/{repo}'."
attempts_made: 1
status: filed
assigned_to: integrator
resolution: ""
resolution_evidence: ""
---

## Reproduction

Started `npm run live` with a disposable `GLACIER_HOME`, installed the `carpenter-prepare-listing` flow through `ventures/install_all.py`, seeded its input files, and ran it through the real Glacier API. The first command node failed before starting the script because the runner resolved `cwd: "{repo}"` as a literal subdirectory of its flow workspace.

Assumptions: command nodes run in a flow workspace; venture scripts are checked into the repository and are not copied into each flow workspace; `cwd` placeholders must be expanded by Glacier for a flow to invoke repository scripts portably.

One config-level attempt used the documented `{repo}` working-directory convention. A fixed absolute repository path would only work in this worker's checkout and would not be a portable venture flow, so it is not a suitable second attempt. A durable fix needs a repository path contract or a venture asset-install mechanism outside this card's `ventures/**` lane.

## Requested follow-up

Integrator: decide the runtime contract for command nodes that invoke installed venture scripts. Keep the fix in the platform lane; do not hard-code this worktree path into the flow. After resolution, rerun the real Glacier flow with current owner-provided product/comparable data and capture evidence.
