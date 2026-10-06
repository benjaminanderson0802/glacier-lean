# Glacier core v0 contract (backend <-> screen). No AI yet.

## Environment file (saved in the vault as `environments/<id>.json`, one git commit per save)
{
  "id": "nightly-tests", "name": "Nightly tests",
  "nodes": [ {"id": "n1", "type": "schedule|command|check|approval|note", "config": {...}, "position": {"x": 0, "y": 0}} ],
  "edges": [ {"id": "e1", "source": "n1", "target": "n2", "label": "" } ]
}
Node configs:
- schedule: {"cron": "*/1 * * * *"}   (start node; also creates/updates a DBOS schedule named after the environment)
- command:  {"cmd": "pytest -q", "cwd": "optional"}   (records exit_code + output)
- check:    {"expr": "exit_code == 0"} evaluated against the PREVIOUS node's result; outgoing edges labelled "yes" / "no"
- approval: {"prompt": "Tests failed. Continue?"}  pauses durably until approved/rejected; outgoing edges "yes" / "no"
- note:     {"path": "runs/{env}-{run}.md", "template": "Run {run} of {env}: {summary}"}  writes to the vault via the memory service (git commit)
A node with several outgoing unlabelled edges runs them in order. Cycles allowed; max 50 node executions per run.

## HTTP API (backend on :8000, all JSON, prefix /api)
- GET  /api/environments                      -> [{id,name}]
- GET  /api/environments/{id}                 -> Environment
- PUT  /api/environments/{id}                 body Environment -> {"saved": true, "commit": "abc123"}
- POST /api/environments/{id}/run             -> {"run_id": "..."}
- GET  /api/runs?env_id=...                   -> [{run_id, env_id, status, started_at}]
- GET  /api/runs/{run_id}                     -> {run_id, env_id, status: running|waiting|done|failed|rejected,
                                                  node_states: {node_id: pending|running|done|failed|waiting|skipped},
                                                  outputs: {node_id: "text"}, waiting_on: node_id|null}
- POST /api/runs/{run_id}/approve             body {"node_id": "...", "approved": true} -> {"ok": true}
- GET  /api/vault/notes                       -> ["runs/x.md", ...];  GET /api/vault/note?path=... -> {"path","body"}
- WS   /api/events  -> messages {"run_id","env_id","node_id","state","output"?} on every node state change

## Durability rules
- Every run is a DBOS workflow; each node execution is a DBOS step. Kill the backend mid-run -> on restart the run resumes, finished nodes are not re-run.
- Approval waits use DBOS messages (recv with long timeout); approving after a restart still works.
- Data folder: GLACIER_HOME (default ./data): vault/ (git), glacier.sqlite (DBOS + app tables).
