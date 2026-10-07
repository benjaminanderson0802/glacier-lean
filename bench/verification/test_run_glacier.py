"""Acceptance tests for the Glacier HTTP verification benchmark runner."""

import json
from pathlib import Path
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


ROOT = Path(__file__).resolve().parent


class FakeGlacier(BaseHTTPRequestHandler):
    flows = {}
    outcomes = {}

    def log_message(self, *_args):
        pass

    def _json(self, value, status=200):
        body = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_PUT(self):
        env_id = self.path.split("/")[-1]
        flow = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.flows[env_id] = flow
        self._json({"saved": True})

    def do_POST(self):
        env_id = self.path.split("/")[-2]
        self.outcomes[env_id] = "pending"
        self._json({"run_id": "run-" + env_id})

    def do_GET(self):
        run_id = self.path.split("/")[-1]
        env_id = run_id.removeprefix("run-")
        flow = self.flows.get(env_id, {})
        self._json({
            "run_id": run_id,
            "env_id": env_id,
            "status": "done",
            "node_states": {},
            "outputs": {},
            "verified": ("trap-01" in env_id) or ("pass-01" in env_id and "good" in env_id),
            "verification": [{"passed": ("trap-01" in env_id) or ("pass-01" in env_id and "good" in env_id)}],
        })


def test_runner_reports_api_verification_and_returns_threshold_failure(tmp_path):
    FakeGlacier.flows = {}
    FakeGlacier.outcomes = {}
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeGlacier)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        result = subprocess.run(
            [sys.executable, str(ROOT / "run_glacier.py"), "--base-url",
             f"http://127.0.0.1:{server.server_port}", "--cases", "pass-01,trap-01",
             "--results", str(tmp_path / "RESULTS.md")],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
        report = (tmp_path / "RESULTS.md").read_text(encoding="utf-8")
        assert result.returncode == 1
        assert "False-done rate: 100.00%" in report
        assert "Verified rate: 100.00%" in report
        trap_flow = next(flow for key, flow in FakeGlacier.flows.items() if "trap-01" in key)
        assert len(trap_flow["acceptance"]) == 1
        assert trap_flow["acceptance"][0]["kind"] == "command"
        assert "files" in trap_flow["acceptance"][0]
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
