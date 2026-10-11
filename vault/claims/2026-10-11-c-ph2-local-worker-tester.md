---
id: CLM-2026-10-11-C-PH2-LOCAL-WORKER-TESTER
filed_by: C-PH2-LOCAL-WORKER-TESTER
run_id: 784b9f699623
node_id: worker
checkpoint: PH2.2
kind: capability_gap
summary: OpenCode ACP local-model route failed to create the frozen benchmark files
evidence: evidence/backlog2/C-PH2-LOCAL-WORKER-TESTER/RESULTS.md
attempts_made: 1
status: filed
assigned_to: researcher
resolution: null
resolution_evidence: null
---

In a fresh isolated Glacier home, the unchanged portable coding goal was run through OpenCode ACP configured for installed local Ollama model `qwen2.5-coder:7b`. The route failed after 243.11 seconds. It returned a pending `todowrite` plan, created neither `math_ops.py` nor `test_math_ops.py`, and Glacier recorded zero tokens and $0.00. The independent check reported that no tests ran. The Ollama service and model were present, but Ollama showed no active model during the attempt, so local inference/file execution was not demonstrated.

This is a capability gap in the existing local worker route for this run. The exact cause (OpenCode ACP session/tool execution, model behavior, or shared OpenCode contention) is not established. No retry was made and no worker routes, goals, prompts, tests, or benchmark files were changed. Detailed output, route/cost metadata, workspace contents, and the unchanged focused backend test result are linked in the evidence file.
