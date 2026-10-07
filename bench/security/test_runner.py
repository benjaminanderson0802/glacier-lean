"""HTTP-level acceptance tests using a tiny fake Glacier API."""
import json
import importlib.util
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import sys
import threading

HERE = Path(__file__).resolve().parent
RUNNER_SPEC = importlib.util.spec_from_file_location(
    "security_run_glacier", HERE / "run_glacier.py"
)
security_run_glacier = importlib.util.module_from_spec(RUNNER_SPEC)
RUNNER_SPEC.loader.exec_module(security_run_glacier)


class FakeAPI(BaseHTTPRequestHandler):
    seen = []

    def log_message(self, *_args):
        pass

    def _send(self, status, body=None, headers=None):
        raw = json.dumps(body or {}).encode()
        self.send_response(status)
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/api/node-types":
            return self._send(200, [])
        if self.path == "/api/memory/notes":
            return self._send(200, [])
        if self.path.startswith("/api/memory/note?"):
            return self._send(400, {"detail": "That note path is not allowed"})
        return self._send(404)

    def do_OPTIONS(self):
        FakeAPI.seen.append(("OPTIONS", self.path, self.headers.get("Origin")))
        return self._send(200, headers={"Access-Control-Allow-Methods": "GET"})

    def do_PUT(self):
        self.rfile.read(int(self.headers.get("Content-Length", "0")))
        return self._send(400, {"detail": "Claims can't be edited from memory"})

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", "0")))
        return self._send(404, {"detail": "not found"})


def test_runner_counts_blocked_http_probes_and_writes_report(tmp_path):
    FakeAPI.seen = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeAPI)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = subprocess.run(
            [sys.executable, str(HERE / "run_glacier.py"), "--base-url",
             f"http://127.0.0.1:{server.server_port}", "--cases", "cors-random-origin,memory-claims-path",
             "--results", str(tmp_path / "RESULTS.md")],
            cwd=HERE, text=True, capture_output=True, timeout=15, check=False,
        )
        report = (tmp_path / "RESULTS.md").read_text()
        assert result.returncode == 0, result.stdout + result.stderr
        assert "Blocked: 2/2" in report
        assert ("OPTIONS", "/api/memory/notes", "https://random.example") in FakeAPI.seen
        assert "NOT BLOCKED" not in report
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_runner_exits_nonzero_when_probe_is_not_blocked(tmp_path):
    class OpenAPI(FakeAPI):
        def do_GET(self):
            self._send(200, {"accepted": True})

        def do_PUT(self):
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            self._send(200, {"accepted": True})

    server = ThreadingHTTPServer(("127.0.0.1", 0), OpenAPI)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = subprocess.run(
            [sys.executable, str(HERE / "run_glacier.py"), "--base-url",
             f"http://127.0.0.1:{server.server_port}", "--cases", "memory-claims-path",
             "--results", str(tmp_path / "RESULTS.md")],
            cwd=HERE, text=True, capture_output=True, timeout=15, check=False,
        )
        assert result.returncode == 1
        assert "Blocked: 0/1" in (tmp_path / "RESULTS.md").read_text()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_schema_requires_exact_status_and_review_attack_shapes():
    cases = [json.loads(path.read_text()) for path in sorted((HERE / "cases").glob("*.json"))]
    by_id = {case["id"]: case for case in cases}
    assert by_id["memory-claims-lookalike"]["request"]["body"]["author"] == "owner"
    assert by_id["memory-claims-path"]["request"]["body"]["author"] == "owner"
    assert by_id["flow-restore-ambiguous"]["request"]["probe"] == "flow_restore_min_length"
    assert by_id["memory-undo-ambiguous"]["request"]["probe"] == "memory_undo_ambiguous"
    assert by_id["run-undo-ambiguous"]["request"]["probe"] == "run_undo_truncated"
    assert by_id["secret-list-leak"]["request"]["probe"] == "secret_list"
    restore = by_id["flow-restore-ambiguous"]["request"]
    assert restore["probe"] == "flow_restore_min_length"
    assert restore["check"] == "min_length_message"
    assert len(restore["body"]["commit"]) == 6


def test_restore_min_length_probe_requires_seven_character_error():
    case = {"id": "flow-restore-ambiguous", "request": {
        "check": "min_length_message", "expected_status": 400,
    }}
    assert security_run_glacier.probe_result(
        case, 400, '{"detail":"Commit id must be at least 7 characters"}', {}
    )["blocked"]
    assert not security_run_glacier.probe_result(
        case, 400, '{"detail":"Commit not found"}', {}
    )["blocked"]


def test_runner_registers_secret_list_case_and_rejects_truncated_run_id(tmp_path):
    class ProbeAPI(FakeAPI):
        def do_PUT(self):
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            if self.path == "/api/secrets/tok":
                ProbeAPI.secret = body["value"]
                return self._send(200, {"saved": True})
            self._send(404)

        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            ProbeAPI.seen.append(("POST", self.path, self.headers.get("Origin")))
            if self.path in {"/api/runs/abcdef/undo", "/api/runs/abc/undo"}:
                self._send(404, {"detail": "Run not found"})
            else:
                self._send(200, {"undone": True})

        def do_GET(self):
            if self.path == "/api/secrets":
                return self._send(200, ["tok"])
            self._send(404)

    ProbeAPI.secret = None
    server = ThreadingHTTPServer(("127.0.0.1", 0), ProbeAPI)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = subprocess.run(
            [sys.executable, str(HERE / "run_glacier.py"), "--base-url",
             f"http://127.0.0.1:{server.server_port}", "--cases",
             "run-undo-ambiguous,secret-list-leak", "--results", str(tmp_path / "RESULTS.md")],
            cwd=HERE, text=True, capture_output=True, timeout=15, check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert ProbeAPI.secret is not None
        assert "Blocked: 2/2" in (tmp_path / "RESULTS.md").read_text()
        assert ("POST", "/api/runs/abcdef/undo", None) in FakeAPI.seen
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
