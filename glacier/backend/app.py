"""Glacier core v0 backend: `uvicorn app:app --port 8000`. Data lives in GLACIER_HOME (default ./data)."""
import os, json, asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from dbos import DBOS, DBOSConfig
import store, vault, plugins, verify

HOME = os.path.abspath(os.environ.get("GLACIER_HOME", "data"))
os.makedirs(HOME, exist_ok=True)
DB_PATH = os.path.join(HOME, "glacier.sqlite")
vault.init(os.path.join(HOME, "vault"))
store.init(DB_PATH)
DBOS(config=DBOSConfig(name="glacier", system_database_url=f"sqlite:///{DB_PATH}"))
import runner  # noqa: E402  (registers workflows after DBOS is configured)

CATALOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "contract", "node_types.json")
with open(CATALOG_PATH) as _f:
    NODE_CATALOG = json.load(_f)["types"]  # single source of truth shared with the screen and the mock server
NODE_CATALOG = NODE_CATALOG + plugins.load_nodes({t["type"] for t in NODE_CATALOG})  # step plug-ins (nodes/)
NODE_TYPES = {t["type"] for t in NODE_CATALOG}


@asynccontextmanager
async def lifespan(_app):
    store.broadcaster.loop = asyncio.get_running_loop()
    DBOS.launch()  # recovers runs that were in flight when the backend died
    yield
    DBOS.destroy()


app = FastAPI(title="Glacier", lifespan=lifespan)
# The desktop app (Tauri) serves the screen from its own origin; only those origins may call the API cross-origin.
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
app.add_middleware(CORSMiddleware, allow_origins=["tauri://localhost", "http://tauri.localhost", "https://tauri.localhost"],
                   allow_methods=["*"], allow_headers=["*"])
from local_guard import LocalRequestGuard  # noqa: E402
import local_token  # noqa: E402
app.add_middleware(LocalRequestGuard)
local_token.get_token()  # create the per-install token file at startup so the desktop app can read it


@app.get("/api/health")
def health():
    """Open liveness check (no data); every other /api path needs the install token."""
    return {"ok": True}

plugins.load_routes(app)  # registers routers in routes/, including the Home summary endpoint


def _env_or_404(env_id: str) -> dict:
    try:
        return runner.load_env(env_id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(404, f"environment {env_id} not found")


@app.get("/api/node-types")
def node_types():
    """Node types, their settings fields and branch labels; the screen builds its palette and forms from this."""
    return NODE_CATALOG


@app.get("/api/environments")
def list_environments():
    envs = [json.loads(vault.read_note(p)) for p in vault.list_notes(".json", "environments")]
    return [{"id": e["id"], "name": e.get("name", e["id"])} for e in envs]


@app.get("/api/environments/{env_id}")
def get_environment(env_id: str):
    return _env_or_404(env_id)


@app.put("/api/environments/{env_id}")
def save_environment(env_id: str, env: dict):
    validate_environment(env_id, env)
    commit = vault.write_note(runner.env_path(env_id), json.dumps(env, indent=2), agent="glacier-api")
    return {"saved": True, "commit": commit}


def validate_environment(env_id: str, env: dict) -> dict:
    """Apply the shared flow validation and scheduling rules before any save."""
    env["id"] = env_id
    env.setdefault("name", env_id); env.setdefault("nodes", []); env.setdefault("edges", [])
    bad = [n.get("type") for n in env["nodes"] if n.get("type") not in NODE_TYPES]
    if bad:
        raise HTTPException(400, f"unknown node types: {bad}")
    try:
        verify.validate(env.get("acceptance"))
    except ValueError as e:
        raise HTTPException(400, str(e))
    try:
        vault.safe_path(runner.env_path(env_id))
        runner.sync_schedule(env)
    except Exception as e:
        raise HTTPException(400, str(e))
    return env


@app.post("/api/environments/{env_id}/run")
def run_environment(env_id: str):
    env = _env_or_404(env_id)
    if env.get("goal") and not env.get("acceptance"):
        raise HTTPException(400, "This goal has no check yet. Add a way to check it is done before running it.")
    return {"run_id": runner.start_run(env_id)}


@app.get("/api/runs")
def list_runs(env_id: str | None = None):
    return store.list_runs(env_id)


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(404, f"run {run_id} not found")
    run["usage"] = store.usage_of(run_id)  # model, route, tokens and cost per step
    graph = store.graph_of(run_id)
    acceptance = graph.get("acceptance") or []
    checks = store.checks_of(run_id)
    run["verification"] = checks
    run["workspace"] = store.workspace_of(run_id)  # isolated runs: branch, merged or not, and why
    if not acceptance:
        run["verified"] = None
    elif run["status"] in ("done", "failed", "rejected"):
        req = [i for i, c in enumerate(acceptance) if c.get("required", True)]
        got = {c["check"]: c["passed"] for c in checks}
        run["verified"] = run["status"] == "done" and all(got.get(i) for i in req)
    else:
        run["verified"] = None
    w = run.get("waiting_on") or ""
    if w.startswith("check-") and w[6:].isdigit() and int(w[6:]) < len(acceptance):
        run["waiting_prompt"] = acceptance[int(w[6:])].get("question", "")
    elif w:
        node = next((n for n in graph.get("nodes", []) if n["id"] == w), None)
        run["waiting_prompt"] = ((node or {}).get("config") or {}).get("prompt", "")
    return run


class Approval(BaseModel):
    node_id: str
    approved: bool


@app.post("/api/runs/{run_id}/approve")
def approve(run_id: str, body: Approval):
    run = get_run(run_id)
    if run["waiting_on"] != body.node_id:
        raise HTTPException(409, f"run {run_id} is not waiting on {body.node_id}")
    DBOS.send(run_id, {"approved": body.approved}, topic=body.node_id)
    return {"ok": True}


@app.get("/api/vault/notes")
def vault_notes():
    return vault.list_notes(".md")


@app.get("/api/vault/note")
def vault_note(path: str):
    try:
        return {"path": path, "body": vault.read_note(path)}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except (FileNotFoundError, IsADirectoryError):
        raise HTTPException(404, f"note {path} not found")


@app.websocket("/api/events")
async def events(ws: WebSocket):
    """Pushes run events to the screen. Listens for the client (or the server shutting down) closing the
    socket at the same time, so a waiting connection never blocks a restart."""
    await ws.accept()
    q = store.broadcaster.subscribe()

    async def pump():
        while True:
            await ws.send_json(await q.get())

    sender = asyncio.create_task(pump())
    try:
        while True:
            receiving = asyncio.create_task(ws.receive())
            done, _ = await asyncio.wait({sender, receiving}, return_when=asyncio.FIRST_COMPLETED)
            if sender in done:  # send failed: socket is gone
                receiving.cancel()
                break
            if receiving.result()["type"] == "websocket.disconnect":
                break
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        sender.cancel()
        store.broadcaster.unsubscribe(q)
