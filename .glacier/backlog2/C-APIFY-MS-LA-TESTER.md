# C-APIFY-MS-LA-TESTER — Independently verify the two existing contractor Actors

Owner: Benjamin. Role: **TESTER only**.

## Scope

Exclusive lane: `apify-existing-actors-evaluator`. Allowed edits: new acceptance checks under `ventures/apify-tools/tests/acceptance/` and `ventures/apify-tools-louisiana/tests/`, `evidence/backlog2/C-APIFY-MS-LA-TESTER/`, and a card-specific claim. Restrict evaluation to the existing Mississippi and Louisiana contractor Actors; do not touch the new Census/FDIC/NPI Actor work assigned to T-APIFY3B, product code, pricing files or Store listings.

## Goal

Independently recheck the existing Actors' source-backed match/no-match/uncertain rows, stale-source handling, output schema, and success-only billing boundary in local SDK mode. This tests the Apify revenue path without publishing, charging, or treating owner canaries as paid users.

Read first: each Actor's `ACCEPTANCE.md`, `PROOF.md`, `README.md`, `ventures/apify-portfolio/PROOF.md`, `ventures/SPEC.md`.

## Drift check

- Checkpoint: PH12.10. PH5/PH9 remain in progress; PH12 is owner-authorized for parallel build work.
- Properties/metrics: P-VERIFY, P-CONTROL; M-VERIFIED, M-AUDIT.
- Existing tools: local Apify SDK, captured public-source fixtures and pytest; no paid service.
- Acceptance first: frozen known records and stale/no-match/outage cases agree with source evidence; only successful readable lookups can emit the configured billable event.

## Verification

Run both Actor suites separately with `~/w/glacier-lean/.venv/bin/python -m pytest -q <suite>`. Use local SDK mode only; do not set live billing, publish, change Console prices or run a paid cloud Actor.
