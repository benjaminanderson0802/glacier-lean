# Glacier core v0 contract (backend <-> screen). The only AI is the optional Codex worker node.

## Environment file (saved in the vault as `environments/<id>.json`, one git commit per save)
{
  "id": "nightly-tests", "name": "Nightly tests",
  "nodes": [ {"id": "n1", "type": "<one of GET /api/node-types>", "config": {...}, "position": {"x": 0, "y": 0}} ],
  "edges": [ {"id": "e1", "source": "n1", "target": "n2", "label": "" } ],
  "max_steps": 500   (optional; step limit per run, default 500)
}
Node types, their settings fields and branch labels are defined once in glacier/contract/node_types.json and served at GET /api/node-types.
Node configs:
- schedule: {"cron": "*/1 * * * *"}   (start node; also creates/updates a DBOS schedule named after the environment)
- command:  {"cmd": "pytest -q", "cwd": "optional"}   (records exit_code + output)
- codex:    {"prompt": "Fix {prev_output}", "workdir": "optional", "sandbox": "read-only|workspace-write", "model": "optional"}
            Codex worker: runs `codex exec --json --skip-git-repo-check -s <sandbox> -C <workdir> -o <file> [-m model] -- <prompt>`
            (binary from env CODEX_BIN, default "codex"; signed in with ChatGPT, no API key; 30 min timeout).
            Prompt placeholders: {env} {run} {prev_output} (= output of the most recent command/codex node, last 8000 chars).
            workdir default GLACIER_HOME/workspaces/<env>; sandbox default workspace-write.
            While running, output is a live log of Codex events (refreshed every ~2s); final output is
            "codex exit <code>\n<last message>". Records exit_code like command. Not installed / not signed in ->
            node fails with "Codex not signed in — run: codex login --device-auth" (or a not-installed message).
- check:    {"expr": "exit_code == 0"} evaluated against the most recent command/codex result; outgoing edges labelled "yes" / "no"
- approval: {"prompt": "Tests failed. Continue?"}  pauses durably until approved/rejected; outgoing edges "yes" / "no"
- note:     {"path": "runs/{env}-{run}.md", "template": "Run {run} of {env}: {summary}"}  writes to the vault via the memory service (git commit)
- command and codex also accept "retries" (0-10; retried with a short pause, output prefixed "[attempt k of n]") and "timeout" (seconds;
  on timeout the command and everything it started is stopped; output ends "[timed out after Ns]")
- alerts:   a run that ends "failed" sends one plain-language alert via Apprise to every URL in GLACIER_ALERT_URLS (comma separated)
            and in the flow's optional "alert_urls" list (ntfy://, mailto://, discord://, json://, ...). Sub-flow failures alert once, via the top-level run.
- loop:     {"times": "3"}  runs its "again" edges N times (body leads back to the loop node), then follows its "done" edges (max 1000)
- flow:     {"env": "<other flow id>"}  runs that saved flow as its own run and waits; output "sub-run <run_id> of <env>: <status>";
            exit_code 0 when the sub-run is done, else 1 (so a check can branch on it); nesting deeper than 5 fails
A failing command/codex/flow node only continues when it feeds a check node. A node with several outgoing unlabelled edges runs them in order. Cycles allowed; max_steps node executions per run (default 500).

## HTTP API (backend on :8000, all JSON, prefix /api)
- GET  /api/node-types                        -> [{type,label,description,fields:[{key,label,placeholder,default,optional?,multiline?,options?,picker?}],branches:[a,b]|null}]
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
