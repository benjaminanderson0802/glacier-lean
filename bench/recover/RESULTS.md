# Recovery benchmark results

Post-merge run after vault Git locking and per-install API authentication. The benchmark used a local backend, fake Codex executable, HTTP API requests, and `--parallel-runs 4`. Recovery timing begins immediately before the undo or restore request and ends after independent file-state verification.

## Latest run

| Scenario | Recovery time | Restored state | Audit coverage | Result |
|---|---:|---|---:|---|
| `run_notes` | 0.306 s | PASS | Not calculated | PASS |
| `flow_restore` | 0.021 s | PASS | Not calculated | PASS |
| `memory_undo` | 0.022 s | PASS | Not calculated | PASS |
| `isolated_code_undo` | Not measured | Run did not merge; undo was not attempted | Not calculated | FAIL |

Headline: 3 of 4 recovery scenarios completed in less than 0.31 s. The isolated coding run was not verified and did not merge, even with an independent `grep -q after answer.txt` acceptance check. Its recovery time is therefore unmeasured. The runner stops before producing complete audit counts, so this run does not establish M-AUDIT coverage and the overall benchmark fails.

The isolated-run failure occurred twice, including once after adding the acceptance check. Further retries are parked in [CLAIM.md](CLAIM.md), per the recovery limit.

## Earlier pre-merge measurement

The earlier run recorded 98.48% audit coverage (65/66) and failed the overwritten-memory and isolated-code recovery cases. Those values predate vault Git locking and are retained here only as historical context; they are not the post-merge result.
