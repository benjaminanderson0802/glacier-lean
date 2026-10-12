# C-PH2-LOCAL-WORKER-TESTER results

## Drift check and acceptance

- Checkpoint: PH2.2. PH2 is in progress; PH1 is also in progress, so this card claims no phase exit.
- Dependencies: PH1 has not reached its exit; this PH2 work is explicitly allowed to start before the PH2 exit gate.
- Properties and metrics: P-PORTABLE and P-VERIFY; M-PORTABLE and M-LOCAL.
- Existing tool: the frozen `bench/portable/run_portable.py` goal and its independent pytest verifier, run through the existing OpenCode ACP/Ollama route. No new model or service was added.
- Acceptance: a fresh isolated Glacier home runs the frozen coding goal on a local model, creates the expected files, passes Glacier's check and the independent pytest check, and records model/route/cost.

## Live route attempt

Command driver used `/home/glacier/w/glacier-lean/.venv/bin/python`, started Glacier from `glacier/backend` with a fresh temporary `GLACIER_HOME`, and called the unchanged `run_case` from `bench/portable/run_portable.py` for its unchanged `CODING_GOAL` and acceptance command. Only OpenCode ACP with the locally installed `qwen2.5-coder:7b` was selected; the Codex route was not invoked. OpenCode's project config points to `http://127.0.0.1:11434/v1`.

The Ollama tags endpoint returned HTTP 200 before the attempt and showed `qwen2.5-coder:7b` installed. The live attempt failed after 243.11 seconds:

- Glacier worker status: `failed`; Glacier acceptance: false.
- Independent pytest check: false, `no tests ran in 0.00s`.
- Workspace contains only the benchmark's `README.md`, `pyproject.toml`, and local `opencode.json`. It has no `math_ops.py` or `test_math_ops.py`.
- Returned worker output was a `todowrite` plan with three pending items, not file changes.
- Glacier usage recorded route `acp/opencode`, model `opencode`, 0 input/output tokens, and $0.00. The selected provider model was `qwen2.5-coder:7b`; Ollama showed no active model during the still-running attempt. Therefore this is not evidence that local inference completed the goal.
- No paid route or model download was used. The isolated Glacier home and install token were temporary and removed at shutdown.

Detailed sanitized result: `qwen25-coder-live/run.json`. Backend lifecycle log: `qwen25-coder-live/backend.log`. The failed task workspace is retained there to show that no requested files were created.

## Focused backend checks

Unchanged command, from `glacier/backend`:

```sh
/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q tests/test_worker_reply_validation.py tests/test_gateway.py tests/test_gateway_preferred.py
```

Result: **28 passed in 5.48s**. Output is in `focused-backend-tests.log`.

## Outcome

Acceptance did not pass, so PH2.2 remains open and the route was not retried. The local service and model were present, but this OpenCode ACP attempt did not reach a successful local-model file task. A card-specific capability-gap claim records the live failure for follow-up. The focused fixtures pass but do not substitute for live proof.
