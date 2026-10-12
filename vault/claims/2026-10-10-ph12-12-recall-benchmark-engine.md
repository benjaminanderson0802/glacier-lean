---
id: claim-ph12-12-recall-benchmark-engine
filed_by: Codex
run_id: local-card-gf-X1
node_id: recall-checker-release-gate
checkpoint: PH12.22
kind: capability_gap
summary: Recall-checker release verification lacks the independently labeled benchmark set and routed second-engine reviewer
evidence: "The PH12.22 independent review says the required 500 recalled + 500 clean labeled cases are absent. Current ventures/recall-checker/tests contain only focused unit fixtures, not the required 1,000 independently labeled items. Review R1 also identifies the missing local-model then second-engine borderline route in ventures/recall_checker.py, which is outside this card's ventures/recall-checker path list."
attempts_made: 0
status: filed
assigned_to: researcher
resolution: ""
resolution_evidence: ""
---

## Required next work

Obtain or create an independently labeled set of 500 known-recalled and 500 known-clean inventory items with source citations and expected outcomes. Then implement the spec's local-model fuzzy review and separate second-engine borderline route in the matching module, add the benchmark without editing the judging check, and prove the false-no-match rate is at most 1%. Do not claim release accuracy or release readiness until that evidence exists. The current focused suite also remains in conflict with the global `no match found in ...` wording rule; see `vault/claims/2026-10-10-ph12-12-recall-output-vocabulary.md`.
