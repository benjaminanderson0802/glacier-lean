# C-FLOW-ASSET-STAGING — Make installed venture scripts available to command nodes

Owner: Benjamin. Role: **BUILDER only**.

## Scope

Exclusive lane: `platform-venture-assets`. Allowed product edits: `ventures/install_all.py` and the smallest required platform installer/workspace module identified by reproduction; add ordinary unit tests under its existing test directory with this card ID. Do not hard-code a worktree path or edit any venture flow, acceptance check, or shared API contract without integrator assignment.

## Goal

Resolve the proven `{repo}`/missing-asset failure for property-tax and carpenter flows, and the install gap affecting venture scripts generally. Provide a portable, bounded way for installed flows to invoke their checked-in script assets from a disposable Glacier home without temporary symlinks.

Read first: `ventures/install_all.py`, `docs/TESTING.md`, claim `2026-10-10-ph12-20-command-cwd-repo-placeholder.md`, `2026-10-10-property-tax-live-flow-root.md`, `ventures/SPEC.md`.

## Drift check

- Checkpoint: PH12.22 integration, unblocking PH12.17 and PH12.20. PH5/PH9 remain in progress; PH12 work is explicitly parallel-authorized.
- Properties/metrics: P-GOALS, P-LOOPS, P-VERIFY; M-VERIFIED, M-SURVIVE.
- Existing tools: existing installer, flow workspace and Python packaging; no custom engine or dependency.
- Acceptance first: a fresh disposable install invokes a staged script from its flow workspace, cannot escape the staged root, and does not depend on the source checkout path.

## Verification

Reproduce one existing failure before editing. Run focused installer/workspace tests and `ventures/tests`; capture a fresh disposable-home real-backend run in the separate tester card. Do not change flows or acceptance checks to hide the platform gap.
