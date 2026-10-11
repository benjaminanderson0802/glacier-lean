---
id: CLM-2026-10-11-F-PH1-FULL-BOARD-UNRELATED-FAILURES
filed_by: F-PH1-AUDIT
run_id: null
node_id: null
checkpoint: PH1
kind: bug
summary: "Full backend board exposes unrelated /api/home and email-template failures"
evidence: "`~/w/glacier-lean/.venv/bin/python -m pytest -q tests` from glacier/backend: 880 passed, 1 skipped, 5 failed. Reproduced with `-k 'test_home_empty_state or test_home_collects_each_need_you_kind_and_counts_steps or test_home_orders_and_caps_needs_and_notes or tpl-email-inbox-note or tpl-email-search-note'`: 5 failed, 26 deselected. Detailed outcomes are in evidence/ph1-runtime-audit-boundaries.md."
attempts_made: 1
status: filed
assigned_to: null
resolution: null
resolution_evidence: null
---

These failures are outside the runtime/audit card's lane. Three failures are in
`tests/test_home_route.py`: the empty-state count is 34 instead of 0, and the
other need-you route expectations fail on counts or run references. Two real
template tests fail: the inbox-trigger node returns `This step starts when a
new email arrives`, and the email-search flow cannot resolve
`EMAIL_APP_PASSWORD`. The focused command audit acceptance and related suites
pass; no unrelated code or acceptance tests were changed here.
