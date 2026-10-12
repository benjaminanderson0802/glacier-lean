# C-FLOW-ASSET-STAGING-TESTER — Verify venture flows from a clean install

Owner: Benjamin. Role: **TESTER only**. Start after C-FLOW-ASSET-STAGING integrates.

## Scope

Exclusive lane: `venture-assets-evaluator`. Allowed edits: new independent checks under `tests/backlog/` and `evidence/backlog2/C-FLOW-ASSET-STAGING-TESTER/`, plus a card-specific claim. No platform or venture implementation edits and no changes to existing acceptance checks.

## Goal

Install the unchanged property-tax and carpenter flows into a fresh disposable Glacier home and prove each invokes its script without an absolute checkout path or manually created symlink. Verify safe uncertainty/missing-input behavior and retain the run IDs and outputs.

Read first: C-FLOW-ASSET-STAGING card, `docs/TESTING.md`, claims `2026-10-10-ph12-20-command-cwd-repo-placeholder.md` and `2026-10-10-property-tax-live-flow-root.md`, both venture `PROOF.md` files.

## Drift check

- Checkpoint: PH12.22, with evidence for PH12.17 and PH12.20. PH12 is explicitly authorized in parallel; no phase exit is claimed.
- Properties/metrics: P-VERIFY, P-LOOPS; M-VERIFIED, M-SURVIVE.
- Existing tools: installer, real backend API and disposable-home fixtures; no new dependency.
- Acceptance first: both fresh-home flows reach their preparation node, source inputs remain fixture-labeled, and missing/uncertain records do not produce a ready-to-file artifact.

## Verification

Use the isolated real-backend method in `docs/TESTING.md` and `~/w/glacier-lean/.venv/bin/python` for relevant tests. Preserve existing checks, use unique ports/home, and stop only the backend started by this card. No portal login, filing or customer data.
