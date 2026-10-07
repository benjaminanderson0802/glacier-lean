import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from conftest import env


class FakeOllama:
    def __init__(self, status=200):
        self.requests = []
        self.status = status
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                owner.requests.append((self.path, body))
                if owner.status != 200:
                    self.send_error(owner.status, "model unavailable")
                    return
                payload = json.dumps({
                    "message": {"role": "assistant", "content": "A local reply"},
                    "prompt_eval_count": 17,
                    "eval_count": 9,
                }).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *_):
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server.server_port}"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def test_local_ai_fills_placeholders_and_records_usage(make_server, monkeypatch):
    with FakeOllama() as ollama:
        monkeypatch.setenv("GLACIER_OLLAMA_URL", ollama.url)
        server = make_server().start()
        flow = env("local-prompt", [
            ("prior", "command", {"cmd": "echo previous result"}),
            ("ai", "local_ai", {"prompt": "For {env}/{run}: {prev_output}", "model": "test-model"}),
        ], [("prior", "ai", "")])
        server.put("/api/environments/local-prompt", flow)
        run_id = server.post("/api/environments/local-prompt/run")["run_id"]
        run = server.wait_run(run_id)
        assert run["status"] == "done"
        assert run["outputs"]["ai"] == "A local reply"
        path, body = ollama.requests[0]
        assert path == "/api/chat"
        assert body["stream"] is False and body["think"] is False
        assert body["model"] == "test-model"
        assert body["messages"][-1]["content"] == f"For local-prompt/{run_id}: previous result\n"
        assert run["usage"]["ai"] == {
            "model": "test-model", "route": "local/ollama", "tokens_in": 17, "tokens_out": 9, "cost_usd": 0.0
        }


def test_local_ai_uses_environment_model_or_default(monkeypatch):
    from nodes.local_ai import DEFAULT_MODEL, run

    captured = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def read(self):
            return json.dumps({"message": {"content": "ok"}}).encode()

    def fake_urlopen(request, timeout):
        captured.append((request.full_url, json.loads(request.data), timeout))
        return Response()

    monkeypatch.setattr("nodes.local_ai.urllib.request.urlopen", fake_urlopen)
    monkeypatch.delenv("GLACIER_OLLAMA_URL", raising=False)
    monkeypatch.setenv("GLACIER_LOCAL_MODEL", "from-env")
    ctx = {"config": {"prompt": "hello", "timeout": 4}, "env_id": "e", "run_id": "r"}

    assert run(ctx)["usage"]["model"] == "from-env"
    assert captured[-1][0] == "http://localhost:11434/api/chat"
    assert captured[-1][1]["model"] == "from-env"
    assert captured[-1][2] == 4

    monkeypatch.delenv("GLACIER_LOCAL_MODEL")
    assert run(ctx)["usage"]["model"] == DEFAULT_MODEL
    assert captured[-1][1]["model"] == DEFAULT_MODEL


def test_local_ai_failure_routes_check_no_with_friendly_message(make_server, monkeypatch):
    monkeypatch.setenv("GLACIER_OLLAMA_URL", "http://127.0.0.1:1")
    server = make_server().start()
    flow = env("local-down", [
        ("ai", "local_ai", {"prompt": "hello", "timeout": 1}),
        ("check", "check", {"expr": "exit_code == 0"}),
        ("yes", "note", {"path": "runs/yes.md", "template": "yes"}),
        ("no", "note", {"path": "runs/no.md", "template": "no"}),
    ], [("ai", "check", ""), ("check", "yes", "yes"), ("check", "no", "no")])
    server.put("/api/environments/local-down", flow)
    run = server.wait_run(server.post("/api/environments/local-down/run")["run_id"])

    assert run["node_states"] == {"ai": "failed", "check": "done", "yes": "skipped", "no": "done"}
    assert run["outputs"]["ai"] == (
        "Local AI is not running at http://127.0.0.1:1. Start Ollama, or pick another worker."
    )
    assert run["outputs"]["check"] == "no"


def test_local_ai_http_error_routes_check_no_with_model_hint(make_server, monkeypatch):
    with FakeOllama(status=404) as ollama:
        monkeypatch.setenv("GLACIER_OLLAMA_URL", ollama.url)
        server = make_server().start()
        flow = env("local-model-missing", [
            ("ai", "local_ai", {"prompt": "hello", "model": "missing-model"}),
            ("check", "check", {"expr": "exit_code == 0"}),
            ("yes", "note", {"path": "runs/yes.md", "template": "yes"}),
            ("no", "note", {"path": "runs/no.md", "template": "no"}),
        ], [("ai", "check", ""), ("check", "yes", "yes"), ("check", "no", "no")])
        server.put("/api/environments/local-model-missing", flow)
        run = server.wait_run(server.post("/api/environments/local-model-missing/run")["run_id"])

    assert run["node_states"] == {"ai": "failed", "check": "done", "yes": "skipped", "no": "done"}
    assert run["outputs"]["ai"] == (
        'Local AI could not use model "missing-model". Download it with: ollama pull missing-model.'
    )
    assert run["outputs"]["check"] == "no"


def test_local_ai_timeout_has_specific_message(monkeypatch):
    from nodes.local_ai import run

    def timed_out(request, timeout):
        raise socket.timeout()

    monkeypatch.setattr("nodes.local_ai.urllib.request.urlopen", timed_out)
    monkeypatch.setenv("GLACIER_OLLAMA_URL", "http://localhost:11434")
    result = run({"config": {"prompt": "hello", "timeout": 7}, "env_id": "e", "run_id": "r"})

    assert result["state"] == "failed" and result["exit_code"] == 1
    assert result["output"] == "Local AI took longer than 7 seconds."


def test_local_ai_nonnumeric_timeout_uses_default(monkeypatch):
    from nodes.local_ai import DEFAULT_TIMEOUT, run

    captured = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def read(self):
            return json.dumps({"message": {"content": "ok"}}).encode()

    def fake_urlopen(request, timeout):
        captured.append(timeout)
        return Response()

    monkeypatch.setattr("nodes.local_ai.urllib.request.urlopen", fake_urlopen)
    result = run({"config": {"prompt": "hello", "timeout": "slow"}, "env_id": "e", "run_id": "r"})

    assert result["state"] == "done"
    assert captured == [DEFAULT_TIMEOUT]


def test_local_ai_appears_in_node_types(server):
    catalog = {item["type"]: item for item in server.get("/api/node-types")}
    assert catalog["local_ai"]["label"] == "Local AI"
    assert catalog["local_ai"]["worker"] is True
    assert {field["key"] for field in catalog["local_ai"]["fields"]} >= {"prompt", "model", "timeout"}
