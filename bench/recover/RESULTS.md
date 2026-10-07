# Recovery benchmark results

## Latest live attempt

The benchmark ran against a local backend with the fake Codex executable under `flock /tmp/glacier-suite.lock` and an outer `timeout 600`. It again stalled during the 50-note run setup before recovery started. The runner/backend pair was stopped cleanly after setup exceeded 120 seconds. The backend's Git `cat-file` helpers were sleeping; the process list also contained old helpers owned by unrelated backends. `py-spy` was unavailable, so no thread stack could be captured. See [STALL.md](STALL.md). This setup delay is not a recovery time.

| Scenario | Latest recovery time | Restored state | Audit coverage | Result vs. 120 s / 100% |
|---|---:|---|---:|---|
| Run writes 50 notes, then undo | Not measured; undo was not reached | Not measured | Not established | FAIL: no valid measurement |
| Restore a flow after 10 edits | Not measured | Not measured | Not established | FAIL: no valid measurement |
| Undo an overwritten memory note | Not measured | Not measured | Not established | FAIL: no valid measurement |
| Undo an isolated coding run merged into workspace | Not measured | Not measured | Not established | FAIL: no valid measurement |

Audit coverage for this attempt: **not established**; the 100% gate is not demonstrated. Overall: **FAIL / incomplete measurement**. The recovery threshold is < 120 seconds; no fresh recovery duration can be compared to it because setup did not reach recovery.

## Prior observations (historical only)

These timings came from an earlier benchmark version. They are retained as context and do not count as fresh results for this revision.

| Scenario | Prior recovery time | Prior restored state | Prior audit evidence |
|---|---:|---|---|
| Run writes 50 notes, then undo | 0.404 s | PASS | 50 run-tagged paths for 50 changed notes |
| Restore a flow after 10 edits | 0.022 s | PASS | 10 version entries for 10 edits |
| Undo an overwritten memory note | 0.022 s | PASS | 1 history entry for 1 overwrite |
| Undo an isolated coding run merged into workspace | 0.200 s | FAIL | No matching run changes in the vault API; undo returned 404 and left the workspace file changed |

An earlier overall figure of 98.39% (61/62) used a different denominator and an API change-count fallback. It is not valid for the current audit definition and is not reported as current coverage.
