# C-PH2-PORTABILITY-TESTER — PH2 portability recheck

Run date: 2026-10-11

## Drift check and acceptance

- Checkpoint: PH2 exit evidence only. PH1 is still `in_progress`; this result does not claim the PH2 exit.
- Properties and metrics: P-PORTABLE and P-VERIFY; M-PORTABLE and M-COST.
- Existing tool: `bench/portable/run_portable.py` and its existing flow builder, independent acceptance checker, and three configured backends. No benchmark file was changed.
- Acceptance written first: all three selected routes must run the identical frozen coding goal and independent check; each must pass Glacier verification and the independent check. Report every route's outcome and cost, retaining failures in the denominator.

## Method

Used the benchmark's `CODING_GOAL`, `CHECK_CMD`, `build_flow`, `normalize_flow`, and `run_case` unchanged, in coding-only mode. The benchmark's normal entry point launches a simpler fallback goal after any coding failure; that fallback was not run because this card requires the exact same frozen goal on all routes. Each run used its own temporary project workspace. The independent check was `/home/glacier/w/workers/gf-C-PH2-PORTABILITY-TESTER/.venv/bin/python -m pytest -q`. The normalized flow snapshots match; only the selected backend fields differ.

Tool versions are in `tool-versions.json`; complete recorded flow snapshots, worker outputs, check output, route, elapsed time, and usage records are in `coding-runs.json`. The isolated backend log is `backend.log`.

## Results

| Backend | Glacier status / check | Independent check | Elapsed | Route | Reported cost |
|---|---|---:|---:|---|---:|
| Codex CLI | done / pass | pass (2 tests) | 18.99 s | `codex/chatgpt-plan` | $0.00; 84,529 input / 517 output tokens |
| OpenCode ACP + Ollama `qwen2.5-coder:7b` | failed / fail | fail (`no tests ran`) | 40.02 s | `acp/opencode` | $0.00; backend reported 0 input / 0 output tokens |
| OpenCode ACP + Ollama `granite3.3:2b` | failed / fail | fail (`no tests ran`) | 26.85 s | `acp/opencode` | $0.00; backend reported 0 input / 0 output tokens |

The two local runs are free local routes. Their zero token figures are missing usage telemetry, not evidence of zero inference. The reported monetary cost is $0.00 for all routes.

**Result: FAIL, 1/3 selected routes passed both checks.** Codex created the requested implementation and tests. Both local workers returned tool-shaped or instructional text without leaving the expected test files; Glacier rejected them and the independent pytest check found no tests. No goal, check, model prompt, or worker configuration was changed to improve a result. The failures remain in the denominator and are linked to the card-specific claim.
