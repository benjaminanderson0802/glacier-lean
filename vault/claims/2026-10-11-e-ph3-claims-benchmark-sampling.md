---
id: CLM-2026-10-11-E-PH3-CLAIMS-BENCHMARK-SAMPLING
filed_by: worker:E-PH3
run_id: ''
node_id: ''
checkpoint: PH3.4
kind: bug
summary: Claims benchmark samples routed claims before specialist proof completes
evidence: evidence/E-PH3/claims-benchmark-followup.md; bench/claims/run_claims.py; bench/claims/test_claims_runner.py
attempts_made: 0
status: filed
assigned_to: verifier
resolution: ''
resolution_evidence: ''
---

## Problem

The live claims benchmark stops polling as soon as claim status leaves `filed` or `researching`. `record_and_route` sets a repairable claim to `routed` and then starts the specialist workflow, which edits the workspace and re-runs the original flow for proof. The benchmark therefore samples the claim before that repair/proof can finish and counts it as unresolved.

## Evidence

`evidence/E-PH3/claims-benchmark-followup.md` reports correct routing for 24/24 cases and zero false auto-resolutions, but only 4/24 resolved. Most expected-to-resolve cases were sampled in `routed` status. The implementation sequence is visible in `bench/claims/run_claims.py::run_cases`, `glacier/backend/claims_research.py::research_claim`, and `glacier/backend/claims_specialist.py::work_claim`.

The runner fixture tests pass, but they do not prove that `run_cases` waits for a specialist proof run. These results are not a valid claims metric remeasurement and must not be used to judge PH3 exit.

## Research

The PH3 card must not edit the benchmark runner or its judging tests. An independent verifier should make the benchmark wait for a terminal outcome (resolved, proposed, or other expected terminal state), retain its evidence requirements, and verify the specialist re-run before recording resolution rates.

## Resolution

Pending independent benchmark correction and rerun. No production claims workflow change or benchmark acceptance change was made here.
