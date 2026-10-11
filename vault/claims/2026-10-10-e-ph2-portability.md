---
id: CLM-2026-10-10-E-PH2-PORTABILITY
filed_by: E-PH2
run_id: 5fd9654d6d70
node_id: worker
checkpoint: PH2
kind: capability_gap
summary: Granite through OpenCode describes file operations instead of executing them
evidence: evidence/ph2/portable-progress.json; evidence/live/portable_three_backends.md
attempts_made: 1
status: filed
assigned_to: researcher
resolution: null
resolution_evidence: null
---

The unchanged bench/portable/run_portable.py coding goal passed via the signed-in
Codex subscription CLI (run 189ae917614b, Glacier's command verifier passed two
tests), but Granite through OpenCode returned prose/tool-shaped text without
creating the requested files. Glacier correctly rejected the run: no tests ran.
The independent tester's simpler fallback remains part of the same benchmark.

Past-fix search found the same Granite failure recorded on 2026-10-08 in
evidence/live/portable_three_backends.md. This is a model/harness tool-use
capability problem, not malformed JSON in Glacier's gateway. No checks or prompts
were weakened, and no model, harness version, or paid route was adopted to force
a pass. A researcher/independent tester should identify a supported free local
coding route and reproduce the same goal before PH2 exit can be claimed.

The Qwen coding route also failed during OpenCode session creation due to its
shared SQLite database being locked (run ab5d5114afd3). This environment issue
belongs with CLM-2026-10-10-E-PH2-LIVE-GAPS; the worker did not alter shared
OpenCode data or stop another worker's process.
