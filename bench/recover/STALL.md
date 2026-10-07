# Recovery benchmark stall record

The revised live attempt was started under `flock /tmp/glacier-suite.lock` with a `timeout 600` outer bound. It did not complete the 50-note run setup, so no recovery endpoint was reached and no M-RECOVER number is available. The `RESULTS.md` from the prior attempt remains the current results and reports this as an incomplete measurement.

## Captured process evidence

At 2026-10-07 10:31:44 UTC, the runner process was PID 775981 and its backend child was PID 775985, listening on `127.0.0.1:49923`. The backend had been alive for about 35 seconds at that snapshot. The benchmark wrapper PID was 774776. At a later check, backend PID 775985 was in a sleeping state with 10.3% accumulated CPU. Its Git subprocesses were both sleeping:

```text
PID     PPID    ELAPSED STAT COMMAND
775985  775981  00:30   S<sl python -m uvicorn app:app --host 127.0.0.1 --port 49923
776053  775985  00:28   S<    git cat-file --batch-check
776054  775985  00:28   S<    git cat-file --batch
```

`ps -ef | grep git` also showed long-lived idle `git cat-file` helpers from unrelated backend processes in other shared worktrees (PIDs 73885/73886, 289930/289931, and 289982/289983). Those processes were not part of this benchmark and were left alone.

`which py-spy` returned no path, so no Python thread stack dump could be captured. No debugger was installed into the shared environment. The benchmark runner and its backend child were stopped with SIGTERM after the setup exceeded the 120-second recovery target; both exited cleanly.

## Suspected cause

The benchmark lock only serializes processes that also acquire `/tmp/glacier-suite.lock`; it cannot prevent unrelated workers' backend processes from accessing their own or shared Git repositories. The observed idle `cat-file` children indicate GitPython's persistent object readers, but the process listing alone does not prove they caused the wait. The long delay appears during repeated per-note Git work in the 50-note flow, potentially amplified by concurrent Git activity in the shared sandbox. A stack dump or an actually exclusive quiet window is needed to distinguish a lock wait, GitPython reader contention, and ordinary slow commit/index work.

This is a setup stall, not a recovery duration. Results must not be interpreted as a measured rollback time.
