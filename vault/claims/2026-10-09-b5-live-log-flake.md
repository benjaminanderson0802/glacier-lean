---
id: CLM-2026-10-09-B5-LIVE-LOG-FLAKE
filed_by: B5
run_id: null
node_id: null
checkpoint: PH1.2
kind: bug
summary: Codex live-log backend test was load-sensitive
evidence: "Original report: two test-only process-gate attempts failed to observe a live output line, while the acceptance test passed alone and failed under the full suite. Resolution: production stdout draining now decouples periodic flushes from line arrival; 20/20 acceptance-test runs passed under concurrent full-suite load, with the existing live-output assertion unchanged."
attempts_made: 2
status: resolved
assigned_to: B6
resolution: "Codex stdout is now drained by a dedicated reader thread into a queue. The runner's main loop waits only until the two-second flush deadline, so a pause between JSONL lines cannot block live output publication. The existing live-output assertion was retained."
resolution_evidence: "glacier/backend/tests/test_core.py::test_codex_streams_live_log_while_running passed 20/20 consecutive invocations while the four-worker backend suite ran concurrently; the focused test had also passed after the change. The full suite completed in 251.10s: 763 passed, 1 skipped, and one unrelated failure in test_assistant_chat_runs.py::test_approved_run_now_starts_one_and_lists_run_and_appends_result_once (expected one 'finished' conversation line, observed zero)."
---

## Root cause

The Codex runner iterated directly over `p.stdout` and checked the two-second flush deadline only after each line arrived. The iterator blocks when the child has no complete JSONL line available, so quiet periods longer than the flush interval prevented the runner from publishing output that had already arrived. Machine load changed scheduling and made the test's observation timing inconsistent; the output pipe itself was line-buffered by the fake and event ordering was not the cause.

## Resolution and verification

The runner now drains stdout on a dedicated reader thread and feeds a queue. The runner loop can wake at the flush deadline even when the queue is empty and publish the accumulated log while the process is still running. The existing acceptance assertion remains unchanged and still requires `thread.started` in running-node output before `codex exit` appears.

- Reproduction before the fix: focused live-log test passed once; the previously filed load-sensitive failure was caused by the blocking read described above.
- After the fix: focused live-log test passed once.
- Load check: `for run in $(seq 1 20); do ... pytest -q tests/test_core.py -k codex_streams_live_log_while_running; done` passed 20/20 while `pytest -q tests -n 4` ran concurrently.
- Concurrent backend suite: 763 passed, 1 skipped, 1 failed in 251.10s. The failure was `test_assistant_chat_runs.py::test_approved_run_now_starts_one_and_lists_run_and_appends_result_once`, which expected one `finished` conversation line and observed zero; it does not exercise Codex stdout streaming and is outside this claim's scope.
