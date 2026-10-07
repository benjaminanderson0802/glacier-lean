# Recovery benchmark stall record

Both attempts ran under `flock /tmp/glacier-suite.lock` with `timeout 600`. The default limit-1 run wrote 50 notes; its last successful recovery request was `POST /api/runs/<run-id>/undo` (HTTP 200). The limit-4 run also wrote 50 notes and completed flow restore and memory undo; its last successful request was `POST /api/memory/undo` (HTTP 200). Neither attempt completed the full scenario matrix, so no recovery timing or audit percentage is established.

After 20 seconds without a completed request, the runner sent SIGUSR1 to the backend, waited 2 seconds, then stopped it with SIGTERM. Full logs are kept in the ignored `stall-logs/` directory.

## Limit-1 evidence

The backend returned HTTP 200 from run undo. At the later diagnostic signal it was idle in the asyncio event loop; the benchmark was waiting in client-side validation. This does not establish a backend stall.

## Limit-4 relevant stack excerpt

```text
File ".../git/db.py", line 67, in store
File ".../git/index/base.py", line 778, in _store_path
File ".../git/index/base.py", line 828, in _entries_for_paths
File ".../git/index/util.py", line 111, in set_git_working_dir
File ".../git/index/base.py", line 968, in add
File ".../glacier/backend/vault.py", line 73, in write_note
File ".../glacier/backend/routes/memory.py", line 104, in put_note
```

The worker was inside GitPython index staging and its object store during a memory-note write. Git index/object processing or contention is the most likely cause; the captured frames do not distinguish those possibilities.
