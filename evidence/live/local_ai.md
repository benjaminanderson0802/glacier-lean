# Live local AI proof — 2026-10-07

## Setup and commands

Ollama was installed and `qwen3:0.6b` was already present (`ollama list`: `qwen3:0.6b`, 522 MB). Its server was stopped, so I started it with `ollama serve` (bound to `127.0.0.1:11434`). The model was loaded locally; no cloud model was used. “Offline” here means no cloud model route was used; this check did not disconnect the machine from the network.

Backend command (from this worktree, isolated data folder, minimal environment):

```sh
cd /workspaces/workers/W11-live/glacier/backend && env -i PATH="$PATH" HOME="$HOME" PYTHONPATH=. GLACIER_HOME=/tmp/w11-live-local-ai GLACIER_LOCAL_MODEL=qwen3:0.6b GLACIER_OLLAMA_URL=http://127.0.0.1:11434 /workspaces/glacier-lean/.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8421
```

The flow `w11-live-local-ai` used a `local_ai` node with model `qwen3:0.6b`, followed by a `check` node (`exit_code == 0`). Its required independent rubric check asked whether the model output was exactly `GLACIER_LOCAL_OK_42`.

Run command:

```sh
curl -fsS -X POST http://127.0.0.1:8421/api/environments/w11-live-local-ai/run -H 'Content-Type: application/json' -d '{}'
```

Run ID: `2f6ae5059e8f`.

## Result

The worker returned the exact token. The graph check passed. The independent rubric check, run by a second local-model call, returned `fail`, so the run is **not verified** (`status: failed`, `verified: false`). This is a real local-model run and an honest verification failure, not a passing completion.

A prior command-acceptance attempt asked the text-only local worker to create a file. The model described the file but did not create it; the command check failed. I then simplified to the exact-token task above. The independent rubric still failed, so no success is claimed.

## Run JSON

```json
{
  "run_id": "2f6ae5059e8f",
  "env_id": "w11-live-local-ai",
  "status": "failed",
  "waiting_on": null,
  "node_states": {"agent": "done", "check": "done"},
  "outputs": {"agent": "GLACIER_LOCAL_OK_42", "check": "yes"},
  "usage": {"agent": {"model": "qwen3:0.6b", "route": "local/ollama", "tokens_in": 28, "tokens_out": 9, "cost_usd": 0.0}},
  "verification": [{"check": 0, "kind": "rubric", "passed": false, "evidence": "reviewer (local model qwen3:0.6b) said fail"}],
  "workspace": null,
  "verified": false
}
```

## Commands and last lines

- `ollama list` — `qwen3:0.6b    7df6b6e09427    522 MB    51 minutes ago`
- `setup/harnesses/verify_opencode.sh` — `OpenCode ACP verified: 1.18.35 (MIT)`
- `curl -fsS http://127.0.0.1:8421/api/runs/2f6ae5059e8f` — `"verified":false`
