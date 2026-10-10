# Freight claims progress — PH12.14

Status: implementation and focused checks are complete; real Glacier flow execution is blocked by the existing platform claim `CLM-PH12-20-CWD-REPO`.

## Drift check

1. Checkpoint: PH12.14, Freight claims.
2. Dependencies: PH12 depends on PH5 and PH9; both phases are still in progress. The owner-approved card authorizes parallel work, so implementation may proceed, but this card cannot mark the checkpoint done before phase exits and the independent audit.
3. Properties and metrics: P-CONTROL and M-AUDIT through human gates and no automatic carrier contact; P-VERIFY and M-VERIFIED through source-linked documents, explicit customer confirmations, and focused checks; the six registered flows aim to support M-TTFA by reusing the shared blocks, but no time-to-first-automation measurement was run.
4. Existing tools: the shared reader, deadline tracker, ShipStation connector, portal filer, and customer layer cover the requirements. This venture adds only orchestration, calculations, and a small read-only label-tracking adapter using the official API. No new dependency or paid service is added.
5. Acceptance: tests prove damaged-item-only valuation, customer confirmations, required documents, insurance gating, carrier-term citation, 30/120-day tracking, contingency arithmetic, no-send defaults, and mock-only filer use. The focused suite passes; the real Glacier flow still needs the command-working-directory blocker resolved.

The venture package now contains six registered flows for ShipStation review, claim deadlines, customer authorization, packet preparation, carrier receipt, and contingency invoice drafts. ShipStation polling remains opt-in after the owner checks API limits. Carrier contacts, signatures, invoices, and payments stay behind human review. The acceptance suite passes 14 tests, and `ventures.install_all --dry-run --only freight-claims` validates all six flows. A local end-to-end packet run passed on synthetic intake, producing `$250.00` of customer-confirmed damaged-item value and a `$200.00` customer-confirmed terms-based liability estimate with no side effects.

A real Glacier session accepted all six flows. Running `freight-prepare-claim` failed before the command started because Glacier treated `cwd: "{repo}"` literally and looked for `/tmp/glacier-live-Dk68RB/workspaces/freight-prepare-claim/{repo}`. The same platform behavior is already documented in `vault/claims/2026-10-10-ph12-20-command-cwd-repo-placeholder.md`; this card does not modify platform files. The run produced no external side effects.

No live ShipStation account or carrier documents were available. The real-runtime intake used synthetic local-only files, so the real-data and carrier-account checks remain owner follow-ups. Customer files currently enter through a local folder because a customer-facing upload link is not available in this lane. Contingency billing is a review-only invoice draft; it does not create a payment link or charge. The Playwright screenshot stayed queued behind both shared heavy slots and was not captured. PH12.14 remains unverified; this venture does not change NORTHSTAR checkpoint status.
