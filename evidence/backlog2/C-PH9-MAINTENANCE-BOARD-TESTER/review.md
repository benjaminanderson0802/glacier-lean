# PH9.1 maintenance Environment independent review

## Drift check and acceptance

- Checkpoint: PH9.1, independent verification only. This does not close the checkpoint.
- Dependencies: PH3 and PH7 exits are owner-approved; PH5 is still in progress, as stated by the card.
- Properties and metrics: P-VERIFY and P-CONTROL; M-VERIFIED and M-AUDIT.
- Existing tools: used the maintenance Environment and its existing health/test board, plus its authenticated backend API. No duplicate runner or dependency was added.
- Acceptance written before execution: in a disposable clone with isolated Python/npm dependencies, unique `GLACIER_HOME`, and unique authenticated loopback backend port, finish the Environment, confirm the proposal note and acceptance check, and confirm the clone has empty `git status --porcelain`. Do not use `/tmp/e2edata`, shared dependencies, port 8000, or either legacy launcher.

## Result

**Not accepted.** The preserved run evidence shows the maintenance Environment did not complete, so no proposal note or successful saved-note acceptance is evidenced. The clone's final status is also unavailable.

The captured API run is `3c367c743cca`, from unique port `36573`. It reached terminal state `failed`; `weekly` was done, `health` failed, and `scan`, `maintenance`, and `status_note` were skipped. The health output reports failures including `tests/test_acp_agent.py::test_acp_denies_move_with_destination_outside_workdir`, `bench/claims/test_C_terminal_outcome.py::test_still_running_routed_claim_is_polled_through_timeout_and_stays_unresolved`, and failures in several venture acceptance suites. Other test groups passed. This review did not diagnose or change those tests.

The interrupted attempt's logs show pinned Python dependencies installed under `/tmp/glacier-ph9-maint-bhyo77/clone` and `npm ci` completed. Its runner source sets a unique `GLACIER_HOME`, a generated port, and an authorization bearer token. However, that temporary root no longer exists, `live-result.json` is empty, and there is no `clone-status.txt`; therefore isolation setup is visible in the captured attempt, but final checkout cleanliness and proposal acceptance are unproven. The saved `run-latest.json`, `run-start.json`, port, install logs, and runner source are retained alongside this report.

## Legacy launcher review (source only)

Neither launcher was executed.

- `setup/run_core_tests.sh` installs into the checkout's shared `.venv` and runs `npm ci` in the shared `glacier/web` dependency directory. It unconditionally removes `/tmp/e2edata`, starts a backend on fixed port 8000 using that path, then runs the browser check against that port. Concurrent workers can lose data, dependency state, or port ownership. Its pytest output is piped through `tail` without `pipefail`, so a failing pytest can be masked by the final pipeline command.
- `setup/live_codex_check.sh` directly targets `http://localhost:8000/api`, sends no engine-token authorization header, and has no readiness check or unique backend/home selection. It can address another worker's backend; with the current auth requirement its unauthenticated requests cannot reliably create or inspect its intended run.

No `/tmp/e2edata` path, shared project dependency directory, or port 8000 was touched by this review. No other worker's process was stopped.

## Escalation

Filed claim `CLM-2026-10-11-C-PH9-MAINTENANCE-HEALTH-FAILURE` for the health-board failure and missing final clone evidence. Per the card's tester-only scope and NORTHSTAR escalation, no test, flow, or launcher was edited and no retry was started after this external test-board failure.

## Anti-pattern check

The captured run shows a verification flow failing before its proposal step, so no done claim is made from partial node completion. The main anti-pattern risk here is treating `weekly: done` or a worker report as proof despite the failed Environment status; this report treats the terminal run status and missing acceptance artifacts as authoritative.
