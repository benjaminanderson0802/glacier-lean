# C-PROPERTY-TAX-FLOW-TESTER — Verify a fresh-home property-tax packet run

Owner: Benjamin. Role: **TESTER only**. Start after C-FLOW-ASSET-STAGING integrates.

## Scope

Exclusive lane: `property-tax-live-evaluator`. Allowed edits: `evidence/backlog2/C-PROPERTY-TAX-FLOW-TESTER/` and a card-specific claim. No flow, platform, packet code or existing test edits.

## Goal

From an isolated Glacier install, run the current Cook County public-row smoke case through the real backend and confirm the flow reaches packet preparation with a dated source result and expected uncertainty where evidence is absent. No owner/customer parcel file or filing.

Read first: `ventures/property-tax/ACCEPTANCE.md`, `PROOF.md`, claim `2026-10-10-property-tax-live-flow-root.md`, C-FLOW-ASSET-STAGING card, `docs/TESTING.md`.

## Drift check

- Checkpoint: PH12.17 and PH12.22. PH12 is explicitly authorized in parallel; the platform asset fix is the only dependency.
- Properties/metrics: P-VERIFY, P-CONTROL; M-VERIFIED, M-AUDIT.
- Existing tools: current installed flow and real-backend fixture harness; no new runner.
- Acceptance first: fresh-home run reaches packet preparation, preserves public source/date, and cannot produce a filing-ready packet with missing customer evidence.

## Verification

Use disposable GLACIER_HOME, unique port and the project interpreter. Capture run ID and outputs. No portal navigation, account login, signatures or filing.
