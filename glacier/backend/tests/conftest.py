"""Each test runs the real backend as a uvicorn subprocess with its own GLACIER_HOME, so kill -9 / restart is realistic."""
import os, sys, time, socket, signal, subprocess
import httpx, pytest

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAKE_CODEX = os.path.join(BACKEND, "tests", "fake_codex.py")  # tests never call the real Codex CLI


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Server:
    def __init__(self, home):
        self.home, self.port, self.proc = str(home), free_port(), None
        self.log = open(os.path.join(self.home, "server.log"), "a")

    @property
    def url(self):
        return f"http://127.0.0.1:{self.port}"

    def start(self):
        env = dict(os.environ, GLACIER_HOME=self.home, CODEX_BIN=FAKE_CODEX)
        options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
        self.proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app:app", "--port", str(self.port)],
                                     cwd=BACKEND, env=env, stdout=self.log, stderr=subprocess.STDOUT, **options)
        deadline = time.time() + float(os.environ.get("GLACIER_TEST_START_TIMEOUT", "60"))
        while time.time() < deadline:  # startup grows with plug-ins; a busy machine can need well over 15 s
            if self.proc.poll() is not None:
                break
            try:
                if httpx.get(self.url + "/api/environments").status_code == 200:
                    return self
            except httpx.HTTPError:
                pass
            time.sleep(0.1)
        raise RuntimeError("server did not start; see " + self.home + "/server.log")

    def kill(self):
        """Simulated power loss: forcibly stop the server and anything it spawned."""
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(self.proc.pid), "/T", "/F"], capture_output=True)
        else:
            os.killpg(self.proc.pid, signal.SIGKILL)
        self.proc.wait()

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(10)
            except subprocess.TimeoutExpired:
                self.kill()

    # helpers
    def get(self, path, **kw):
        r = httpx.get(self.url + path, timeout=30, **kw); r.raise_for_status(); return r.json()

    def put(self, path, body):
        r = httpx.put(self.url + path, json=body, timeout=30); r.raise_for_status(); return r.json()

    def post(self, path, body=None):
        r = httpx.post(self.url + path, json=body, timeout=30); r.raise_for_status(); return r.json()

    def wait_run(self, run_id, statuses=("done", "failed", "rejected"), timeout=30):
        deadline = time.time() + timeout
        while time.time() < deadline:
            run = self.get(f"/api/runs/{run_id}")
            if run["status"] in statuses:
                return run
            time.sleep(0.2)
        raise AssertionError(f"run {run_id} never reached {statuses}: {run}")


@pytest.fixture
def server(tmp_path):
    s = Server(tmp_path).start()
    yield s
    s.stop()


@pytest.fixture
def make_server(tmp_path):
    made = []
    def make():
        s = Server(tmp_path); made.append(s); return s
    yield make
    for s in made:
        s.stop()


def env(env_id, nodes, edges):
    """Build an environment: nodes = [(id, type, config)], edges = [(source, target, label)]."""
    return {"id": env_id, "name": env_id.replace("-", " ").title(),
            "nodes": [{"id": i, "type": t, "config": c, "position": {"x": 0, "y": 0}} for i, t, c in nodes],
            "edges": [{"id": f"e{k}", "source": s, "target": t, "label": l} for k, (s, t, l) in enumerate(edges)]}
