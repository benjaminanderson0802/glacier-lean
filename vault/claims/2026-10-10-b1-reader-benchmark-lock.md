---
id: CLM-2026-10-10-B1-READER-BENCHMARK-LOCK
filed_by: B1
run_id: null
node_id: null
checkpoint: PH12.4
kind: environment
summary: Shared heavy-run lock has prevented the reader release benchmark from starting
evidence: "`flock /tmp/glacier-heavy.lock /home/glacier/w/glacier-lean/.venv/bin/python -m ventures.blocks.reader.benchmark ventures/blocks/reader/samples/manifest.json` has remained queued for more than 15 minutes. `ps` shows other workers' backend suites, UI checks, and e2e runs queued or using the shared lock. The command has not run and produced no benchmark output."
attempts_made: 1
status: filed
assigned_to: null
resolution: null
resolution_evidence: null
---

This is shared-environment contention outside the reader/rules lane. I reproduced
it with the required benchmark command and left other workers' processes alone.
The reader/rules focused test suite had passed once before the final PDF layout
changes, and code compilation plus direct rules checks pass, but neither is a
substitute for the release benchmark. The benchmark and post-change focused suite
remain queued under the shared lock; run them after the queued sandbox tests drain.
