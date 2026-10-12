---
id: CLM-2026-10-10-B-HEALTH-VENTURES-SUITE-FAILURES
filed_by: Codex
run_id: card/B-HEALTH-VENTURES
node_id: null
checkpoint: PH11.1
kind: bug
summary: Isolated venture health board repeatedly reports five venture acceptance failures outside the health lane
evidence: "evidence/backlog/B-HEALTH-VENTURES/venture-board.json records the 29-suite isolated board: 23 passed and 6 failed. The same five non-filer failures reproduced in two sequential runs: al-bid-triage duplicate deadlines, al-license-verify mock 503 uncertainty, fba-fee-check NaN validation, job-closeout rate-limit handling, and sam-amendment-alerts duplicate conflict handling. The shared filer failure is already tracked by CLM-2026-10-10-PH12-14-FILER-PLAYWRIGHT-MISSING."
attempts_made: 2
status: filed
assigned_to: null
resolution: null
resolution_evidence: null
---

## Impact

The integration health report now includes each isolated suite and correctly fails overall when these five suites fail. The failures prevent a green venture board; their causes and owners have not been investigated in this health lane.

## Reproduced failures

- `ventures/al-bid-triage/tests/acceptance/test_al_bid_triage.py::test_conflicting_duplicate_deadlines_not_silently_dropped`
- `ventures/al-license-verify/tests/acceptance/test_al_license_verify.py::test_mock_actor_outage_has_customer_uncertainty[503]`
- `ventures/fba-fee-check/tests/acceptance/test_fba_fee_check.py::test_nonfinite_or_malformed_amount_rejected[NaN]`
- `ventures/job-closeout/tests/acceptance/test_job_closeout.py::test_partial_or_failed_source_never_delivers_packet[rate_limit]`
- `ventures/sam-amendment-alerts/tests/acceptance/test_sam_amendment_alerts.py::test_partial_data_rejected_or_uncertain[duplicate_conflict]`

The shared filer test `ventures/blocks/filer/tests/test_filer_acceptance.py::PortalFilerAcceptanceTests::test_submit_requires_approval` also failed and is already documented by `CLM-2026-10-10-PH12-14-FILER-PLAYWRIGHT-MISSING`.

## Required resolution

Route each listed failure to its venture owner for independent triage. Preserve all acceptance checks. Rerun the isolated board after the owners provide fixes or evidence that a failure is environmental; no venture implementation or acceptance check was changed by this card.
