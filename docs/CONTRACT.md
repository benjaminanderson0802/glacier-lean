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
- decide:   {"question": "Which team? {prev_output}", "options": "Billing, Tech support, Other", "engine": "auto|local|codex", "model": "optional"}
            picks exactly one option (the AI's answer is constrained to the list; anything else fails the step) and follows the
            outgoing edge whose label equals that option (case-insensitive). Context = previous step's output. Engines are free:
            local = Ollama (GLACIER_OLLAMA_URL, GLACIER_LOCAL_MODEL), codex = Codex CLI default model; auto = local, then codex.
            Output "decided: <option> (by <engine>)". 2-12 options.
- loop:     {"times": "3"}  runs its "again" edges N times (body leads back to the loop node), then follows its "done" edges (max 1000)
- flow:     {"env": "<other flow id>"}  runs that saved flow as its own run and waits; output "sub-run <run_id> of <env>: <status>";
            exit_code 0 when the sub-run is done, else 1 (so a check can branch on it); nesting deeper than 5 fails
A failing command/codex/flow node only continues when it feeds a check node. A node with several outgoing unlabelled edges runs them in order. Cycles allowed; max_steps node executions per run (default 500).

## Plug-ins and further contracts
New step types and API routes are plug-ins (glacier/backend/plugins.py, docs/contracts/WORKERS.md). Memory v2: docs/contracts/MEMORY.md. Verification and claims: docs/contracts/VERIFICATION.md.

## HTTP API (backend on :8000, all JSON, prefix /api)
- GET  /api/node-types                        -> [{type,label,description,fields:[{key,label,placeholder,default,optional?,multiline?,options?,picker?}],branches:[a,b]|null,branches_from?:"options"}]
- GET  /api/environments                      -> [{id,name}]
- GET  /api/environments/{id}                 -> Environment
- PUT  /api/environments/{id}                 body Environment -> {"saved": true, "commit": "abc123"}
- POST /api/environments/{id}/run             -> {"run_id": "..."}
- GET  /api/runs?env_id=...                   -> [{run_id, env_id, status, started_at}]
- GET  /api/runs/{run_id}                     -> {run_id, env_id, status: running|waiting|done|failed|rejected,
                                                  node_states: {node_id: pending|running|done|failed|waiting|skipped},
                                                  outputs: {node_id: "text"}, waiting_on: node_id|null,
                                                  usage: {node_id: {model, route, tokens_in, tokens_out, cost_usd}}}
- GET  /api/home                             -> {local_ai:{online,model}, counts:{running,need_you},  (local_ai.online is null until the first local-AI check finishes, a few seconds after start)
                                                  needs_you:[{kind,title,detail,at,ref}],
                                                  running:[{run_id,env_id,name,status,step,steps,started_at}],
                                                  recent_notes:[{path,summary,at}]}; one read-only Home summary.
                                                  Needs-you rows are newest first (up to 20): waiting approvals,
                                                  claims proposed for an owner decision, and failures from the last
                                                  seven days. Running includes running, queued and waiting runs;
                                                  step/steps counts completed/total nodes. Recent committed memory
                                                  notes are newest first (up to 10). Local AI discovery is cached
                                                  for 10 seconds and does not block the response on tool probes.
- POST /api/runs/{run_id}/approve             body {"node_id": "...", "approved": true} -> {"ok": true}
- GET  /api/vault/notes                       -> ["runs/x.md", ...];  GET /api/vault/note?path=... -> {"path","body"}
- WS   /api/events  -> run messages {"run_id","env_id","node_id","state","output"?} on every node state change; memory writes publish {"type":"memory","path":"<note path>","action":"write"|"delete","author":"<writer>","run_id":"<run id or empty>"} after the vault git commit succeeds. Events use action `write` for a note write, merge, archive, or undo restoration and `delete` for an actual note deletion. Publish runs outside the vault lock so a slow socket never blocks note writers.
- GET  /api/memory/graph?limit=N -> graph of the N most recently updated notes plus their direct links; omit `limit` for the full graph.

## Durability rules
- Every run is a DBOS workflow; each node execution is a DBOS step. Kill the backend mid-run -> on restart the run resumes, finished nodes are not re-run.
- Approval waits use DBOS messages (recv with long timeout); approving after a restart still works.
- Data folder: GLACIER_HOME (default ./data): vault/ (git), glacier.sqlite (DBOS + app tables).
