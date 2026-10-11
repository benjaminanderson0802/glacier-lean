---
id: CLM-2026-10-11-C-PH2-PORTABILITY-TESTER
filed_by: C-PH2-PORTABILITY-TESTER
run_id: null
node_id: worker
checkpoint: PH2
kind: capability_gap
summary: OpenCode ACP local model routes again failed the frozen portable coding goal
evidence: evidence/backlog2/C-PH2-PORTABILITY-TESTER/result.md; evidence/backlog2/C-PH2-PORTABILITY-TESTER/coding-runs.json
attempts_made: 1
status: filed
assigned_to: researcher
resolution: null
resolution_evidence: null
---

The exact unchanged `bench/portable/` coding goal and independent pytest check were run on Codex CLI, OpenCode ACP with Ollama qwen2.5-coder:7b, and OpenCode ACP with Ollama granite3.3:2b. Codex passed. Both local runs failed Glacier verification and the independent check (`no tests ran`); their recorded output is tool-shaped or instructional text rather than successful file creation. See the linked evidence for versions, route, reported cost, normalized flow, raw worker output, and timings.

This independently reproduces the local-route failure already described by CLM-2026-10-10-E-PH2-PORTABILITY. No task prompt, harness, or model configuration was changed. This tester did not diagnose or modify the workers; the existing claim remains the broader research thread.
