"""Installed self-build flows must run on machines without a `python` command and with every placeholder filled."""
import json
import re
import shlex
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from conftest import BACKEND

ROOT = Path(BACKEND).parents[1]
sys.path.insert(0, str(ROOT / "setup" / "selfbuild"))
import run_card  # noqa: E402

BARE_PYTHON = re.compile(r"(?<![\w./-])python(?=\s)")


def test_fill_command_replaces_placeholders_and_every_bare_python():
    out = run_card.fill_command("cd glacier/backend && python -m pytest -q tests; python {guard} --baseline-root {baseline}",
                                guard="/g/guard.py", baseline="/b")
    assert "{guard}" not in out and "{baseline}" not in out and "/g/guard.py" in out and "/b" in out
    assert not BARE_PYTHON.search(out)
    assert out.count(shlex.quote(sys.executable)) == 2
    assert run_card.fill_command("echo glacier/python stays") == "echo glacier/python stays"


def test_installed_flows_have_no_bare_python_and_no_placeholders(tmp_path):
    card = tmp_path / "card.md"
    card.write_text("Build a tiny feature", encoding="utf-8")
    seen = []

    class API(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_PUT(self):
            seen.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
            self.wfile.write(b'{"saved":true}')

        def do_POST(self):
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
            self.wfile.write(b'{"run_id":"abc123"}')

    api = HTTPServer(("127.0.0.1", 0), API)
    threading.Thread(target=api.serve_forever, daemon=True).start()
    source = tmp_path / "source"
    subprocess.run(["git", "init", "-q", "-b", "main", str(source)], check=True)
    (source / "README.md").write_text("toy", encoding="utf-8")
    subprocess.run(["git", "-C", str(source), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(source), "-c", "user.name=t", "-c", "user.email=t@x", "commit", "-qm", "start"], check=True)
    try:
        result = subprocess.run([sys.executable, str(ROOT / "setup/selfbuild/run_card.py"), str(card),
                                 "--api", f"http://127.0.0.1:{api.server_port}",
                                 "--home", str(tmp_path / "home"), "--source", str(source)], text=True, capture_output=True)
        assert result.returncode == 0, result.stderr
        commands = [n["config"]["cmd"] for flow in seen for n in flow["nodes"] if n["type"] == "command"]
        commands += [c["cmd"] for flow in seen for c in flow.get("acceptance", []) if c.get("kind") == "command"]
        assert len(seen) == 2 and commands
        for cmd in commands:
            assert not BARE_PYTHON.search(cmd), cmd
            assert "{guard}" not in cmd and "{baseline}" not in cmd, cmd
    finally:
        api.shutdown(); api.server_close()
