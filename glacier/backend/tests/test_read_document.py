import http.server
import json
import os
import socketserver
import subprocess
import sys
import threading
from pathlib import Path
from urllib.error import HTTPError

import pytest

from nodes.read_document import NODE


def test_importing_app_does_not_import_document_conversion_stack(tmp_path):
    backend = os.path.dirname(os.path.dirname(__file__))
    env = dict(os.environ, GLACIER_HOME=str(tmp_path / "home"))
    result = subprocess.run(
        [sys.executable, "-c",
         "import app, json, sys; print(json.dumps({name: name in sys.modules for name in "
         "('markitdown', 'magika', 'onnxruntime')}))"],
        cwd=backend, env=env, capture_output=True, text=True, check=True,
    )
    imports = json.loads(result.stdout.splitlines()[-1])
    assert imports == {"markitdown": False, "magika": False, "onnxruntime": False}


FIXTURES = Path(__file__).parent / "fixtures" / "docs"


def context(home, source, **config):
    workspace = Path(home) / "workspaces" / "demo"
    workspace.mkdir(parents=True, exist_ok=True)
    return {
        "env_id": "demo",
        "run_id": "run-1",
        "node_id": "read",
        "config": {"source": source, **config},
        "prev": None,
        "home": str(home),
        "log": lambda _text: None,
    }


def test_reads_html_file_as_plain_text(tmp_path):
    workspace = tmp_path / "workspaces" / "demo"
    workspace.mkdir(parents=True)
    (workspace / "page.html").write_bytes((FIXTURES / "sample.html").read_bytes())

    result = NODE["run"](context(tmp_path, "page.html"))

    assert result["state"] == "done"
    assert result["exit_code"] == 0
    assert "Quarterly notes" in result["output"]
    assert "<h1>" not in result["output"]
    assert result["usage"] == {
        "model": "markitdown", "route": "local/markitdown",
        "tokens_in": 0, "tokens_out": 0, "cost_usd": 0,
    }


def test_reads_csv_file_as_text(tmp_path):
    workspace = tmp_path / "workspaces" / "demo"
    workspace.mkdir(parents=True)
    (workspace / "data.csv").write_bytes((FIXTURES / "sample.csv").read_bytes())

    result = NODE["run"](context(tmp_path, "data.csv"))

    assert result["state"] == "done"
    assert "Harbor" in result["output"] and "17" in result["output"]


def test_refuses_file_outside_flow_workspace(tmp_path):
    outside = tmp_path / "private.txt"
    outside.write_text("secret")

    result = NODE["run"](context(tmp_path, "../../private.txt"))

    assert result["state"] == "failed"
    assert "Only files inside this flow's folder can be read" in result["output"]
    assert result["exit_code"] != 0


def test_refuses_url_host_not_in_allowlist(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_ALLOWED_HOSTS", "example.org")

    result = NODE["run"](context(tmp_path, "https://localhost:12345/page"))

    assert result["state"] == "failed"
    assert "Glacier is not allowed to reach localhost. Add it to the allowed sites first." == result["output"]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def test_reads_allowed_url_from_local_http_server(tmp_path, monkeypatch):
    handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(FIXTURES), **kwargs)
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        monkeypatch.setenv("GLACIER_ALLOWED_HOSTS", "127.0.0.1")
        try:
            result = NODE["run"](context(tmp_path, f"http://{host}:{port}/sample.html"))
        finally:
            server.shutdown()
            thread.join(timeout=2)

    assert result["state"] == "done"
    assert "Quarterly notes" in result["output"]


def test_does_not_follow_redirect_to_unapproved_host(tmp_path, monkeypatch):
    class RedirectHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(302)
            self.send_header("Location", "http://example.org/private")
            self.end_headers()

        def log_message(self, *_args):
            pass

    with socketserver.TCPServer(("127.0.0.1", 0), RedirectHandler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        monkeypatch.setenv("GLACIER_ALLOWED_HOSTS", "127.0.0.1")
        try:
            result = NODE["run"](context(tmp_path, f"http://{host}:{port}/redirect"))
        finally:
            server.shutdown()
            thread.join(timeout=2)

    assert result["state"] == "failed"
    assert result["output"] == "Glacier is not allowed to reach example.org. Add it to the allowed sites first."


def test_truncates_output_with_note(tmp_path):
    workspace = tmp_path / "workspaces" / "demo"
    workspace.mkdir(parents=True)
    (workspace / "long.txt").write_text("abcdefghij")

    result = NODE["run"](context(tmp_path, "long.txt", max_chars=5))

    assert result["state"] == "done"
    assert result["output"].startswith("abcde")
    assert "truncated" in result["output"].lower()
    assert len(result["output"]) <= 100
