---
id: CLM-PH12-22-COOP-STALE-TEST
filed_by: I2
run_id: null
node_id: null
checkpoint: PH12.22
kind: bug
summary: Co-op acceptance test expects the pre-merge missing-rules environment
evidence: "Independent `heavy .venv/bin/python -m pytest -q ventures` run: `ventures/coop-postcards/tests/test_workflow.py::CoOpWorkflowAcceptanceTests::test_claim_requires_preapproval_and_shared_rules_pass_before_filing` fails because it expects `uncertain` with a comment that the shared rules block is absent; after B1 merge the block exists and `check_claim` returns `pass` for the complete valid fixture. Test was not edited under I-04."
attempts_made: 1
status: filed
assigned_to: null
resolution: null
resolution_evidence: null
---

## Reproduction

Ran the integrated venture suite in the I2 worktree. The test fails only on its expected verdict; `ventures.blocks.rules` imports and returns `pass` for the complete sample. The test comment and expectation describe the pre-merge worktree.

## Required resolution

An independent evaluator should decide how the test should assert the post-merge contract without weakening the check. Do not edit this test as part of I2; it judges the co-op workflow, and the failure is reported in `ventures/AUDIT-wave2.md`.
