# Recovery benchmark results

## Measurement status: incomplete

Both requested attempts were run serially with `flock /tmp/glacier-suite.lock` and `timeout 600`, using a local backend and fake Codex. The backend log and stall procedure are described in [STALL.md](STALL.md); raw logs are preserved in the ignored `stall-logs/` folder.

| Scenario | Limit 1 | Limit 4 | Recovery time | Audit coverage |
|---|---|---|---|---|
| Run writes 50 notes, then undo | 50 notes completed; undo returned HTTP 200; state verification did not complete | 50 notes completed; attempt did not reach run undo | Not established | Not established |
| Restore a flow after 10 edits | Not reached | Restore returned HTTP 200 | Not established | Not established |
| Undo an overwritten memory note | Not reached | Undo returned HTTP 200 | Not established | Not established |
| Undo isolated coding run merged into workspace | Not reached | Not reached | Not established | Not established |

The <120 s recovery and 100% audit gates are **not demonstrated**. The benchmark exits nonzero on incomplete/failed measurements. The limit-4 attempt still encountered a stall in GitPython index staging; see the stack excerpt in [STALL.md](STALL.md). The default attempt reached a successful run-undo response, but its independent verification did not finish, so it is not reported as a passing recovery.
