"""Each test runs the real backend as a uvicorn subprocess with its own GLACIER_HOME, so kill -9 / restart is realistic."""
import os, sys, time, socket, signal, subprocess
import httpx, pytest

# Make subprocess-created Git commits independent of the host's global config.
os.environ.setdefault("GIT_AUTHOR_NAME", "Glacier Tests")
os.environ.setdefault("GIT_AUTHOR_EMAIL", "glacier-tests@localhost")
os.environ.setdefault("GIT_COMMITTER_NAME", "Glacier Tests")
os.environ.setdefault("GIT_COMMITTER_EMAIL", "glacier-tests@localhost")

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAKE_CODEX = os.path.join(BACKEND, "tests", "fake_codex.py")  # tests never call the real Codex CLI

# Every test engine uses one known install token (GLACIER_TOKEN overrides the token file), and test HTTP calls to
# a local engine carry it automatically. Tests about refusals send no token or a wrong one explicitly
# (see test_local_token.py), using raw_httpx below.
TEST_TOKEN = "glacier-test-token"
# Tests never read the developer's real OpenCode sessions; a test that needs some points this at its own folder.
os.environ["GLACIER_OPENCODE_DATA"] = os.path.join(os.path.dirname(BACKEND), ".no-opencode-in-tests")
os.environ["GLACIER_CLAUDE_CODE_DATA"] = os.path.join(os.path.dirname(BACKEND), ".no-claude-code-in-tests")
os.environ["GLACIER_GEMINI_DATA"] = os.path.join(os.path.dirname(BACKEND), ".no-gemini-in-tests")
os.environ["GLACIER_TOKEN"] = TEST_TOKEN
# Tests never talk to a real Ollama on this machine; a test that needs one starts a fake and sets this itself.
os.environ["GLACIER_OLLAMA_URL"] = "http://127.0.0.1:9"

# Server subprocesses do their own command discovery. Shadow only the Ollama CLI
# so its `list` fallback cannot read models installed on the developer's machine.
_TEST_BIN = os.path.join(os.path.dirname(BACKEND), ".test-bin")
os.makedirs(_TEST_BIN, exist_ok=True)
if os.name == "nt":
    with open(os.path.join(_TEST_BIN, "ollama.cmd"), "w", encoding="utf-8") as _fake_ollama:
        _fake_ollama.write("@echo NAME ID SIZE MODIFIED\r\n")
else:
    _fake_ollama_path = os.path.join(_TEST_BIN, "ollama")
    with open(_fake_ollama_path, "w", encoding="utf-8") as _fake_ollama:
        _fake_ollama.write("#!/bin/sh\nprintf 'NAME ID SIZE MODIFIED\\n'\n")
    os.chmod(_fake_ollama_path, 0o755)
os.environ["PATH"] = _TEST_BIN + os.pathsep + os.environ.get("PATH", "")
raw_httpx = {name: getattr(httpx, name) for name in ("get", "post", "put", "patch", "delete", "options", "head", "stream", "request")}
_LOCAL = ("http://127.0.0.1", "http://localhost")


def _auth(kw):
    headers = dict(kw.pop("headers", None) or {})
    if not any(key.lower() == "authorization" for key in headers):
        headers["Authorization"] = f"Bearer {TEST_TOKEN}"
    kw["headers"] = headers
    return kw


def _wrap(name):
    original = raw_httpx[name]
    if name == "request":
        def call(method, url, *args, **kw):
            return original(method, url, *args, **(_auth(kw) if str(url).startswith(_LOCAL) else kw))
    else:
        def call(url, *args, **kw):
            return original(url, *args, **(_auth(kw) if str(url).startswith(_LOCAL) else kw))
    return call


for _name in raw_httpx:
    setattr(httpx, _name, _wrap(_name))

try:  # live-events WebSocket in tests: add ?token= (browsers cannot set WebSocket headers either)
    import websockets.sync.client as _ws_client
    _ws_connect = _ws_client.connect

    def _ws_with_token(uri, *args, **kw):
        if uri.startswith(("ws://127.0.0.1", "ws://localhost")) and "token=" not in uri:
            uri += ("&" if "?" in uri else "?") + "token=" + TEST_TOKEN
        return _ws_connect(uri, *args, **kw)
    _ws_client.connect = _ws_with_token
except ImportError:  # pragma: no cover
    pass


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
        log = self.diagnostics()
        self.stop()
        raise RuntimeError(f"server did not start; backend log follows:\n{log}")

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
        if not self.log.closed:
            self.log.flush()
            self.log.close()

    def diagnostics(self) -> str:
        """Return the backend's own log, including output flushed just before failure."""
        if not self.log.closed:
            self.log.flush()
        try:
            with open(os.path.join(self.home, "server.log"), encoding="utf-8", errors="replace") as stream:
                return stream.read()
        except OSError as exc:
            return f"Could not read backend log: {exc}"

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


def _track_server(request, server):
    servers = getattr(request.node, "_backend_test_servers", None)
    if servers is None:
        servers = request.node._backend_test_servers = []
    servers.append(server)


@pytest.fixture
def server(tmp_path, request):
    s = Server(tmp_path)
    _track_server(request, s)
    s.start()
    yield s
    s.stop()


@pytest.fixture
def make_server(tmp_path, request):
    made = []
    def make():
        s = Server(tmp_path)
        made.append(s)
        _track_server(request, s)
        return s
    yield make
    for s in made:
        s.stop()


def env(env_id, nodes, edges):
    """Build an environment: nodes = [(id, type, config)], edges = [(source, target, label)]."""
    return {"id": env_id, "name": env_id.replace("-", " ").title(),
            "nodes": [{"id": i, "type": t, "config": c, "position": {"x": 0, "y": 0}} for i, t, c in nodes],
            "edges": [{"id": f"e{k}", "source": s, "target": t, "label": l} for k, (s, t, l) in enumerate(edges)]}


def pytest_configure(config):
    # Timing and stress tests are run on their own (CI: -m serial without -n) so the
    # parallel batch cannot slow them down; they are checked exactly as before.
    config.addinivalue_line("markers", "serial: run outside the parallel batch")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if not report.failed:
        return
    servers = list(getattr(item, "_backend_test_servers", ()))
    fixture_server = getattr(item, "funcargs", {}).get("server")
    if fixture_server is not None:
        servers.append(fixture_server)
    seen = set()
    for server in servers:
        if id(server) in seen:
            continue
        seen.add(id(server))
        report.sections.append((f"backend server log (stdout/stderr; {server.home})", server.diagnostics()))
