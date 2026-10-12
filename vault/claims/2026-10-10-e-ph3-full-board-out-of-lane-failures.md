---
id: CLM-2026-10-10-E-PH3-FULL-BOARD-OUT-OF-LANE-FAILURES
filed_by: worker:E-PH3
run_id: ''
node_id: ''
checkpoint: PH3.2
kind: bug
summary: Full backend board repeats template runtime and Home route failures outside the PH3 lane
evidence: evidence/E-PH3/backend-full-followup.log; evidence/ventures/final2-backend-tests.log; evidence/ventures/i5-isolated-backend.log
attempts_made: 0
status: filed
assigned_to: debugger
resolution: ''
resolution_evidence: ''
---

## Problem

The full backend suite on `card/gf-E-PH3` completed with 826 passed, 1 skipped, and 6 failed. The failures are three parametrized template runtime cases (`tpl-email-inbox-note`, `tpl-email-search-note`, `tpl-local-data-pipeline`) and three Home route cases (`test_home_empty_state`, `test_home_collects_each_need_you_kind_and_counts_steps`, `test_home_orders_and_caps_needs_and_notes`). None is in the PH3 verification/workspace test files. Similar template and Home route failures appear in earlier committed PH12 evidence linked above.

## Evidence

The full run used the project virtualenv and the shared suite lock. Pytest reported `6 failed, 826 passed, 1 skipped` in `846.80s`. Template outputs include an unsupported event-trigger step, an unset `EMAIL_APP_PASSWORD`, and a structured AI response that did not parse as JSON. Home route failures include expected needs-you fields missing from the returned records. See `backend-full-followup.log` for the exact case list and command result.

## Research

These cases touch template and Home route behavior outside this PH3 card. No fix was attempted here. Earlier committed PH12 backend logs show recurrence; a debugger should compare current template assumptions, route behavior, and fixture setup against those runs.

## Resolution

Pending triage and repair in the owning lane. This claim does not block review of the PH3-only verification tests, but the full backend board is not green.
