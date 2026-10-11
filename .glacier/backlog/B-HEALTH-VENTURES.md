# B-HEALTH-VENTURES — Include isolated venture suites in integration health reporting

Owner: Benjamin. Proposed launch card from T-FIND, 2026-10-10. Read [INDEX.md](INDEX.md#launch-contract), AGENTS.md, NORTHSTAR.yaml and ORCHESTRATION.yaml first. Commit on `card/B-HEALTH-VENTURES`; never push.

## Scope

Allowed edits: `setup/health_check.py; new setup/venture_health.py`. Also allowed: `evidence/backlog/B-HEALTH-VENTURES/` and a card-specific claim in `vault/claims/`. New ordinary unit tests must live under the affected module’s `tests/unit/` and use this card ID in the filename; no existing test edits. Existing tests, acceptance files and CHECK.md files are read-only. No other paths are authorized.

Exclusive lane: **health**. PH11 health code only; E-PH9 owns maintenance/self-build workflows. Do not edit setup/test_health_check.py or active flows.

## Goal and evidence

Health command_specs covers backend, older suites and verification benchmark but omits ventures; historical combined venture collection collides on generic src/scripts imports.

Run each venture/block test directory in a separate process with bounded time and a truthful per-suite result. Preserve existing health output/API, distinguish failed/skipped/not-run, and avoid overlapping heavy jobs.

Read first:

- [setup/health_check.py](../../setup/health_check.py) (command_specs)
- [ventures/OWNER-GUIDE-TESTS.md](../../ventures/OWNER-GUIDE-TESTS.md)

## Drift check

- Checkpoint: **PH11.1**. Properties: **P-LOOPS, P-VERIFY**. Metrics: **M-SURVIVE, M-VERIFIED**.
- Dependencies: use the phase ledger in INDEX; assignment permits scoped work, not a phase-exit claim. Recheck dependencies at dispatch; no NORTHSTAR status edits here.
- Existing-tool choice (I-01): Existing health runner and pytest subprocesses; no CI platform, scheduler or new bookkeeping layer.
- Value/effort estimate: **4/5 value ÷ 2 effort units = 2.00**. Estimates prioritize impact and unblocking, not promised revenue.

## Verification — specified before implementation

Independent fixtures show a failing suite or collection error makes the report fail, a skipped live canary is never labeled live proof, and separate suites with colliding module names both execute. Then run the real isolated board.

Run `~/w/glacier-lean/.venv/bin/python -m pytest -q setup/test_health_check.py`. Builders first reproduce the defect and have an independent evaluator freeze any missing acceptance case; ordinary unit tests do not substitute for that evaluator. Tester-only cards never repair the product they judge. Follow the launch contract for real-backend proof and final reporting.

Finish with commit hash, changed files, commands/results, fixture versus real evidence, and remaining owner steps. Do not send, publish, sign, file, spend, create accounts, delete owner data or decide legal questions. Use synthetic/local evidence unless an already-authorized read-only source is available.
