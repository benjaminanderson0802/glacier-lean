"""Run + node state tables (in glacier.sqlite next to DBOS's tables) and the in-process WebSocket broadcaster."""
import contextlib, json, sqlite3, asyncio, threading
from datetime import datetime, timezone

DB = ""


def init(path: str) -> None:
    global DB
    DB = path
    with _conn() as c:
        # DBOS and Glacier's run-state tables share this file. WAL avoids the
        # rollback journal's extra sync for each durable state transition; FULL
        # sync keeps the completed commits durable across power loss.
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("""CREATE TABLE IF NOT EXISTS glacier_runs(run_id TEXT PRIMARY KEY, env_id TEXT, status TEXT,
                     started_at TEXT, graph TEXT, waiting_on TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS glacier_nodes(run_id TEXT, node_id TEXT, state TEXT, output TEXT,
                     PRIMARY KEY(run_id, node_id))""")
        c.execute("""CREATE TABLE IF NOT EXISTS glacier_workspace(run_id TEXT PRIMARY KEY, info TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS glacier_checks(run_id TEXT, idx INTEGER, kind TEXT, passed INTEGER,
                     evidence TEXT, PRIMARY KEY(run_id, idx))""")
        c.execute("""CREATE TABLE IF NOT EXISTS glacier_usage(run_id TEXT, node_id TEXT, model TEXT, route TEXT,
                     tokens_in INTEGER, tokens_out INTEGER, cost_usd REAL, PRIMARY KEY(run_id, node_id))""")


SQLITE_BUSY_TIMEOUT_SECONDS = 5


@contextlib.contextmanager
def _conn():
    """One short-lived connection per call, always closed (sqlite3's own 'with' only commits, it never closes),
    SQLite arbitrates concurrent connections. Do not hold a process-wide lock while SQLite waits for
    DBOS or another process to release its file lock: readers and unrelated run updates must proceed."""
    c = sqlite3.connect(DB, timeout=SQLITE_BUSY_TIMEOUT_SECONDS)
    try:
        c.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_SECONDS * 1000}")
        c.execute("PRAGMA synchronous=FULL")
        yield c
        c.commit()
    finally:
        c.close()


def create_run(run_id: str, env_id: str, graph: dict) -> None:
    """Insert the run with its graph snapshot and every node pending. No-op if it already exists."""
    with _conn() as c:
        if c.execute("SELECT 1 FROM glacier_runs WHERE run_id=?", (run_id,)).fetchone():
            return
        c.execute("INSERT INTO glacier_runs VALUES (?,?,?,?,?,NULL)", (run_id, env_id, "running",
                  datetime.now(timezone.utc).isoformat(timespec="seconds"), json.dumps(graph)))
        c.executemany("INSERT INTO glacier_nodes VALUES (?,?,?,NULL)", [(run_id, n["id"], "pending") for n in graph["nodes"]])


def graph_of(run_id: str) -> dict:
    with _conn() as c:
        return json.loads(c.execute("SELECT graph FROM glacier_runs WHERE run_id=?", (run_id,)).fetchone()[0])


def mark_chat_reported(run_id: str) -> bool:
    """Atomically claim the one-time conversation report for a completed chat run."""
    with _conn() as c:
        row = c.execute("SELECT graph FROM glacier_runs WHERE run_id=?", (run_id,)).fetchone()
        if not row:
            return False
        graph = json.loads(row[0])
        if not graph.get("_assistant_conversation_id") or graph.get("_assistant_reported"):
            return False
        graph["_assistant_reported"] = True
        c.execute("UPDATE glacier_runs SET graph=? WHERE run_id=?", (json.dumps(graph), run_id))
        return True


def set_run(run_id: str, status: str, waiting_on: str | None = None) -> None:
    with _conn() as c:
        # A canceled run stays canceled: a step that was still finishing must not bring it back to life.
        c.execute("UPDATE glacier_runs SET status=?, waiting_on=? WHERE run_id=? AND status != 'canceled'",
                  (status, waiting_on, run_id))


def set_waiting(run_id: str, env_id: str, node_id: str) -> None:
    """Atomically publish a run-level wait and the node that owns the decision."""
    with _conn() as c:
        c.execute("UPDATE glacier_runs SET status='waiting', waiting_on=? WHERE run_id=? AND status != 'canceled'",
                  (node_id, run_id))
        c.execute("UPDATE glacier_nodes SET state='waiting' WHERE run_id=? AND node_id=?", (run_id, node_id))
    broadcaster.publish({"run_id": run_id, "env_id": env_id, "node_id": node_id, "state": "waiting"})


def set_node(run_id: str, env_id: str, node_id: str, state: str, output: str | None = None) -> None:
    if output is not None:
        import secrets_store
        try:
            output = secrets_store.redact(str(output))
        except Exception:
            output = "[output hidden: secrets could not be checked]"
    with _conn() as c:
        if output is None:
            c.execute("UPDATE glacier_nodes SET state=? WHERE run_id=? AND node_id=?", (state, run_id, node_id))
        else:
            c.execute("UPDATE glacier_nodes SET state=?, output=? WHERE run_id=? AND node_id=?", (state, output, run_id, node_id))
    msg = {"run_id": run_id, "env_id": env_id, "node_id": node_id, "state": state}
    if output is not None:
        msg["output"] = output
    broadcaster.publish(msg)


def skip_pending(run_id: str, env_id: str) -> None:
    with _conn() as c:
        ids = [r[0] for r in c.execute("SELECT node_id FROM glacier_nodes WHERE run_id=? AND state='pending'", (run_id,))]
    for node_id in ids:
        set_node(run_id, env_id, node_id, "skipped")


def list_runs(env_id: str | None) -> list[dict]:
    q, args = "SELECT run_id, env_id, status, started_at FROM glacier_runs", ()
    if env_id:
        q, args = q + " WHERE env_id=?", (env_id,)
    with _conn() as c:
        rows = c.execute(q + " ORDER BY started_at DESC, rowid DESC", args).fetchall()
    return [dict(zip(("run_id", "env_id", "status", "started_at"), r)) for r in rows]


def record_usage(run_id: str, node_id: str, u: dict) -> None:
    """Accumulate token and cost totals; model and route describe the latest execution."""
    with _conn() as c:
        # Existing installations already have this table and primary key; an UPSERT
        # preserves all existing rows while accumulating subsequent executions.
        c.execute("""INSERT INTO glacier_usage VALUES (?,?,?,?,?,?,?)
                     ON CONFLICT(run_id,node_id) DO UPDATE SET
                     model=excluded.model, route=excluded.route,
                     tokens_in=glacier_usage.tokens_in+excluded.tokens_in,
                     tokens_out=glacier_usage.tokens_out+excluded.tokens_out,
                     cost_usd=glacier_usage.cost_usd+excluded.cost_usd""",
                  (run_id, node_id, str(u.get("model") or ""), str(u.get("route") or ""), int(u.get("tokens_in") or 0),
                   int(u.get("tokens_out") or 0), float(u.get("cost_usd") or 0.0)))


def record_check(run_id: str, idx: int, kind: str, passed: bool, evidence: str) -> None:
    import secrets_store
    try:
        evidence = secrets_store.redact(str(evidence))
    except Exception:
        evidence = "[evidence hidden: secrets could not be checked]"
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO glacier_checks VALUES (?,?,?,?,?)", (run_id, idx, kind, int(bool(passed)), evidence))


def record_workspace(run_id: str, info: dict) -> None:
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO glacier_workspace VALUES (?,?)", (run_id, json.dumps(info)))


def workspace_of(run_id: str) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT info FROM glacier_workspace WHERE run_id=?", (run_id,)).fetchone()
    return json.loads(row[0]) if row else None


def checks_of(run_id: str) -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT idx, kind, passed, evidence FROM glacier_checks WHERE run_id=? ORDER BY idx", (run_id,)).fetchall()
    return [{"check": i, "kind": k, "passed": bool(p), "evidence": e} for i, k, p, e in rows]


def usage_of(run_id: str) -> dict:
    with _conn() as c:
        rows = c.execute("SELECT node_id, model, route, tokens_in, tokens_out, cost_usd FROM glacier_usage WHERE run_id=?",
                         (run_id,)).fetchall()
    return {n: {"model": m, "route": r, "tokens_in": ti, "tokens_out": to, "cost_usd": cu} for n, m, r, ti, to, cu in rows}


def get_run(run_id: str) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT run_id, env_id, status, waiting_on, graph FROM glacier_runs WHERE run_id=?", (run_id,)).fetchone()
        if not row:
            return None
        nodes = c.execute("SELECT node_id, state, output FROM glacier_nodes WHERE run_id=?", (run_id,)).fetchall()
    snapshot = json.loads(row[4])
    return {"run_id": row[0], "env_id": row[1], "status": row[2], "waiting_on": row[3],
            "author": snapshot.get("_author", "owner"),
            "node_states": {n: s for n, s, _ in nodes}, "outputs": {n: o for n, _, o in nodes if o is not None}}


class Broadcaster:
    """Fan-out to WebSocket clients. publish() is safe from any thread (DBOS steps run in worker threads)."""

    def __init__(self):
        self.loop: asyncio.AbstractEventLoop | None = None
        self.queues: set[asyncio.Queue] = set()
        self._lock = threading.Lock()

    def subscribe(self) -> asyncio.Queue:
        q = asyncio.Queue()
        with self._lock:
            self.queues.add(q)
        return q

    def unsubscribe(self, q) -> None:
        with self._lock:
            self.queues.discard(q)

    def publish(self, msg: dict) -> None:
        if self.loop is None or self.loop.is_closed():
            return
        with self._lock:
            for q in list(self.queues):
                self.loop.call_soon_threadsafe(q.put_nowait, msg)


broadcaster = Broadcaster()
