# Backend performance on Windows

## Findings

The CI logs point to repeated filesystem durability work and repeated Git history queries as avoidable costs on Windows. NTFS plus antivirus scanning makes each small SQLite journal and Git process more expensive than on the Linux runner. The folder backup test starts a process for each configured template command; its 30-second wait was reached with the copy and checks complete while later note steps were still pending. Windows runs also repeatedly queried vault history during API polling and the concurrency test, and SQLite's default rollback journal added syncs to the run-state and vault indexes.

The concurrency log `job121b.log` shows `test_concurrent_vault_api_reads_and_writes` taking 74.20 seconds before a client `ReadTimeout`. The suite logs `job120.log` and `job_113167691182.log` report 497.80 and 416.59 seconds overall. These logs are evidence of the Windows symptom; the Linux measurements below isolate the relevant code paths but do not reproduce Windows filesystem or antivirus costs.

## Changes

- Put the run-state database and rebuildable vault search index in SQLite WAL mode. Connections explicitly retain `synchronous=FULL`, so completed writes remain durable.
- Initialize the vault index schema once rather than issuing schema creation statements on each connection.
- Cache note history until the note changes, with a bounded cache and invalidation after normal and multi-note vault transactions.
- Cache run change history per run ID and invalidate it when a matching run commit is written.
- Cache exact immutable flow commit lookups used during restore.

Git commits remain authoritative, and each note write still creates its own commit. Template command execution semantics are unchanged; each configured command still starts its own process.

## Linux measurements

Measurements were taken on the Linux shared runner using the target pytest cases and `strace -f -c -e trace=execve,fsync,fdatasync`. `execve` totals include failed PATH probes; “successful starts” counts the successful execs. Wall time includes pytest and server startup and varies with shared-host load. The optimized concurrency pass was also timed without tracing, because strace made that stress test time out under concurrent host load.

| Workload | Before | After | Notes |
| --- | --- | --- | --- |
| One vault note save (`test_memory_write_metadata_and_event`) | 8.99 s; 13 successful process starts; 88 `fdatasync` calls | 6.42 s; 13 successful process starts; 47 `fdatasync` calls | About 47% fewer fdatasync calls. Test wall time includes server startup. |
| Folder backup template (`test_folder_backup_commands_use_absolute_glacier_home_in_real_run`) | 12.62 s; 19 successful process starts; 200 `fdatasync` calls | 5.23 s; 19 successful process starts; 96 `fdatasync` calls | About 52% fewer fdatasync calls. Command process starts are required by the template. |
| Vault concurrency stress (`test_concurrent_vault_api_reads_and_writes`) | 21.84 s, passed without tracing; strace run took 282.05 s and timed out under contention | 32.00 s, passed while a second backend suite was running; strace run took 252.33 s and timed out after all 600 writes | Timing is not a fair before/after comparison because the host load differed. The traced run made 1,596 successful process starts and 3,288 `fdatasync` calls after the change; the baseline trace stopped earlier and is not comparable. History and run-change polling caches reduced repeated Git log invocations. |

The single-save and folder tests show fewer durability syncs, while their subprocess totals stay the same because those paths still use Git and configured shell commands. The stress test's first trace recorded 1,756 successful starts before it stopped; the later trace recorded 1,596 after processing all 600 writes. Both trace runs timed out under tracing and shared-host contention. Plain test wall times therefore should not be interpreted as a measured speedup for concurrency.

## Verification

Added focused tests in `glacier/backend/tests/test_vault_performance.py` for WAL/FULL settings, current search results, history cache invalidation, run change cache invalidation, and exact flow restore lookup reuse. The full backend suite result for this worktree was 555 passed, 1 skipped, and 1 unrelated failure in `tests/test_starter.py::test_apply_creates_only_chosen_flows_once_and_saves_settings`; the assertion expected `granite3.3:2b`, but the starter returned `qwen3:0.6b`.
