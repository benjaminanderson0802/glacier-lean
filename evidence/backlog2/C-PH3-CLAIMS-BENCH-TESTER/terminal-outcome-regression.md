# C-PH3-CLAIMS-BENCH-TESTER — terminal outcome regression

## Drift check and acceptance

- Checkpoint: PH3.4. PH3.2 is still in progress, and this independent test is
  parallel-safe. This is not a PH3.4 metric remeasurement or checkpoint status
  change.
- Property and metrics: P-VERIFY; M-FALSE-DONE and M-VERIFIED.
- Existing tools: the current claims benchmark and pytest. No new framework is
  needed; the test calls the runner's existing `run_cases` entry point.
- Acceptance: a simulated specialist-routed claim must be polled until its
  proof-backed terminal claim state; terminal `resolved` without linked proof
  must not count as resolved; `proposed` is terminal and unresolved; a claim
  still `routed` at timeout must stay unresolved.

## Frozen cases

`bench/claims/test_C_terminal_outcome.py` is the independent frozen check. The
resolved case returns `routed`, `routed`, then `resolved` with
`resolution_evidence=run:proof-run-17`. The still-running case remains `routed`
through a simulated timeout. The remaining two cases check that a bare
`resolved` status without linked evidence is not scored and that `proposed`
remains an owner escalation.

The current runner exits its polling loop as soon as a status leaves `filed` or
`researching`, so it samples the first `routed` observation. The two polling
cases fail against that behavior. Existing denominator and evidence checks are
untouched. The resolved fixture models completion through the claim's
proof-backed terminal state; it does not claim a live benchmark result.

## Verification

Commands run from the repository root:

```text
~/w/glacier-lean/.venv/bin/python -m pytest -q bench/claims/test_C_terminal_outcome.py
2 failed, 2 passed

~/w/glacier-lean/.venv/bin/python -m pytest -q bench/claims
2 failed, 10 passed
```

Both failures are the frozen polling regressions:

- `test_routed_claim_is_not_sampled_until_specialist_proof_is_terminal` —
  observed one poll instead of three.
- `test_still_running_routed_claim_is_polled_through_timeout_and_stays_unresolved`
  — observed one poll instead of continuing through timeout.

`test_terminal_status_without_linked_proof_does_not_count_as_resolved` and
`test_proposed_is_terminal_but_not_a_resolved_sample` pass. All 8 pre-existing
`bench/claims` tests pass.

## Handoff

Builder should change only the benchmark implementation so it waits through
`routed` until the proof-backed claim outcome is terminal or times out. Keep
the existing denominator, `_has_evidence` requirements, and judging tests
unchanged. Re-run this frozen check and `pytest -q bench/claims` after the
builder change.
