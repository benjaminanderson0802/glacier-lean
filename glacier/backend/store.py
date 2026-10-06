"""Run + node state tables (in glacier.sqlite next to DBOS's tables) and the in-process WebSocket broadcaster."""
import contextlib, json, sqlite3, asyncio, threading
from datetime import datetime, timezone

DB = ""


def init(path: str) -> None:
    global DB
    DB = path
    with _conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS glacier_runs(run_id TEXT PRIMARY KEY, env_id TEXT, status TEXT,
                     started_at TEXT, graph TEXT, waiting_on TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS glacier_nodes(run_id TEXT, node_id TEXT, state TEXT, output TEXT,
                     PRIMARY KEY(run_id, node_id))""")


_lock = threading.Lock()


@contextlib.contextmanager
def _conn():
    """One short-lived connection per call, always closed (sqlite3's own 'with' only commits, it never closes),
    serialized in-process so DBOS worker threads and the API never write over each other."""
    with _lock:
        c = sqlite3.connect(DB, timeout=30)
        try:
            c.execute("PRAGMA busy_timeout=30000")
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


def set_run(run_id: str, status: str, waiting_on: str | None = None) -> None:
    with _conn() as c:
        c.execute("UPDATE glacier_runs SET status=?, waiting_on=? WHERE run_id=?", (status, waiting_on, run_id))


def set_node(run_id: str, env_id: str, node_id: str, state: str, output: str | None = None) -> None:
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


def get_run(run_id: str) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT run_id, env_id, status, waiting_on FROM glacier_runs WHERE run_id=?", (run_id,)).fetchone()
        if not row:
            return None
        nodes = c.execute("SELECT node_id, state, output FROM glacier_nodes WHERE run_id=?", (run_id,)).fetchall()
    return {"run_id": row[0], "env_id": row[1], "status": row[2], "waiting_on": row[3],
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
