# Independent runtime audit boundary findings

Run: 2026-10-11, worktree `card/C-PH1-AUDIT-TESTER`.

The independent acceptance suite was run with the project interpreter alongside the existing audit resilience tests:

```text
cd glacier/backend
/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q tests/test_C_runtime_audit_boundaries.py tests/test_audit_log_resilience.py
```

Result: **5 failed, 3 passed in 43.19s**. The 3 passing tests are the existing resilience checks. The 5 failures are new boundary acceptance failures:

- Both successful and failed fake commands ran their side effect before any `step.command_started` row was visible to the command. A correlated `step.command_executed` row is written afterward with its exit code.
- Two retry effects have `step.command_executed` rows with attempts and exit codes, but no start rows for either attempt.
- Simulated runner interruption after the fake command wrote its temporary marker leaves no start record and no explicit interrupted/unknown outcome.
- With `audit.sqlite` unavailable, the fake command writes its marker, `audit_log` emits a warning, and the runner returns `{"state": "done", "exit_code": 0}` without an audit status. The existing resilience test also passes while requiring that the command remain successful in this condition.

The newly defined acceptance semantics therefore disagree with the current audit event placement and unavailable-store behavior. Meeting the start/unknown and audit-availability assertions requires runtime and event/result semantics outside this tester-only file lane. Per the card, no shared contract or runtime code was changed. This evidence should be attached to the existing claim `CLM-2026-10-10-E-PH1-AUDIT-EXIT-PROOF`; the claim itself is outside this card's allowed paths.

## Conclusion

The evidence does not establish M-AUDIT = 100%. PH1 must remain in progress pending a runtime/event contract decision and implementation by the authorized lane, followed by a rerun of these independent cases. The output and filesystem effects from the fake commands remained in pytest temporary directories.
