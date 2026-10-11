---
id: CLM-2026-10-11-B-DIBBS-INTAKE-LEGACY-TESTS
filed_by: Codex
run_id: null
node_id: null
checkpoint: PH12.19
kind: unclear_spec
summary: Existing DIBBS tests expect bid rows from inputs without the provenance now required by B-DIBBS-INTAKE
evidence: "After implementing fail-closed source and owner-confirmation checks, `/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/dibbs-supply/tests` reports 2 failures and 24 passes. `test_prepares_ranked_batch_with_exact_part_supplier_and_margin` and `test_daily_feed_alert_stays_visible_even_when_a_local_quote_matches` supply no source provenance or owner-confirmation digests, yet expect ranked rows. Card scope makes existing tests read-only, while its acceptance requires rows to bind explicit owner confirmations."
attempts_made: 1
status: filed
assigned_to: integrator
resolution: ""
resolution_evidence: ""
---

## Question for the integrator

The implementation follows the card's fail-closed acceptance: a row is withheld unless both local source files match their declared SHA-256 values and each current input record has a matching owner confirmation. The two existing unit tests use legacy input records and therefore cannot reach their expected match result. This card forbids editing existing tests, and the task's acceptance case must remain independent of ordinary unit tests.

Please decide which separately authorized follow-up should reconcile the legacy fixtures with the new record contract. Until then, keep these tests unchanged; do not weaken provenance validation or treat unconfirmed records as owner-confirmed.

## Reproduction

- Baseline before implementation: `20 passed`.
- After implementation: `2 failed, 24 passed`; failures are exactly the two tests named above.
- New focused tests: `8 passed` for matching provenance, trace output, part/quantity/supplier/revision mutations, changed source bytes, supersession, and missing confirmation.
