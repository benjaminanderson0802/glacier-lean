# Contract: AI workers and step plug-ins (frozen for wave 1; changes only through the integrator)

## Adding a step type (no shared files touched)
Create `glacier/backend/nodes/<name>.py` defining `NODE = {"catalog": {...}, "run": fn}` (full rules in `glacier/backend/plugins.py`).
- `catalog`: same shape as an entry of `glacier/contract/node_types.json` (`type, label, description, fields, branches`, optional `branches_from`), plus `"worker": true` for steps that do work and have an exit code.
- `run(ctx) -> result`. ctx: `env_id, run_id, node_id, config, prev, home, log(text)`. result: `state` (done|failed), `output` (text), `exit_code` (workers), optional `branch`, optional `usage`.
- The step appears automatically in GET /api/node-types and on the screen. Never edit runner.py, app.py or node_types.json for a new step.
- Tests go in `glacier/backend/tests/test_<name>.py` and run from glacier/backend: `python -m pytest -q tests`.

## Every AI worker step returns usage
`usage = {"model": str, "route": str, "tokens_in": int, "tokens_out": int, "cost_usd": float}`
- `route` names who served it: `codex/chatgpt-plan`, `local/ollama`, `acp/<harness>`, `gateway/<provider>`.
- `cost_usd` is 0.0 for local models and subscription plans. Owner policy: paid routes are off (proposal required).
- GET /api/runs/{id} returns `usage: {node_id: usage}`.

## Prompt placeholders (all AI worker steps)
`{env}`, `{run}`, `{prev_output}` (last 8000 chars of the previous worker step's output). Context notes from memory are added by the memory contract (MEMORY.md, "context for workers").

## Worker defaults
Model policy (ORCHESTRATION.yaml): Codex default model is the sandbox setting (GPT-6 Luna, low effort); local default GLACIER_LOCAL_MODEL (qwen3:0.6b in the sandbox, larger on the owner's PC); Ollama at GLACIER_OLLAMA_URL (default http://localhost:11434).
