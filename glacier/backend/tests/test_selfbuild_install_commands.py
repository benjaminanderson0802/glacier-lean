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
    (source / "setup").mkdir()
    (source / "setup/requirements.txt").write_text("sample==1.0\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(source), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(source), "-c", "user.name=t", "-c", "user.email=t@x", "commit", "-qm", "start"], check=True)
    try:
        original_argv = sys.argv
        sys.argv = [str(ROOT / "setup/selfbuild/run_card.py"), str(card),
                    "--api", f"http://127.0.0.1:{api.server_port}",
                    "--home", str(tmp_path / "home"), "--source", str(source)]
        original_install = run_card.install_practice_requirements
        run_card.install_practice_requirements = lambda _repo: None
        try:
            assert run_card.main(sys.argv[1:]) == 0
        finally:
            run_card.install_practice_requirements = original_install
            sys.argv = original_argv
        commands = [n["config"]["cmd"] for flow in seen for n in flow["nodes"] if n["type"] == "command"]
        commands += [c["cmd"] for flow in seen for c in flow.get("acceptance", []) if c.get("kind") == "command"]
        assert len(seen) == 2 and commands
        for cmd in commands:
            assert not BARE_PYTHON.search(cmd), cmd
            assert "{guard}" not in cmd and "{baseline}" not in cmd, cmd
    finally:
        api.shutdown(); api.server_close()


def test_install_practice_requirements_uses_exact_requirements_file(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(run_card.subprocess, "run",
                        lambda command, **kwargs: calls.append((command, kwargs)))
    repo = tmp_path / "practice"
    requirements = repo / "setup" / "requirements.txt"
    requirements.parent.mkdir(parents=True)
    requirements.write_text("pinned==1.0\n", encoding="utf-8")

    run_card.install_practice_requirements(repo)

    assert len(calls) == 1
    command, options = calls[0]
    assert command == [str(Path(sys.executable)), "-m", "pip", "install", "-r",
                       str(requirements)]
    assert options["cwd"] == repo
    assert options["check"] is True


def test_run_card_installs_requirements_before_posting_flow(tmp_path, monkeypatch, capsys):
    events = []
    card = tmp_path / "card.md"
    card.write_text("Build a small flow change", encoding="utf-8")
    source = tmp_path / "source"
    subprocess.run(["git", "init", "-q", "-b", "main", str(source)], check=True)
    (source / "setup").mkdir()
    (source / "setup/requirements.txt").write_text("pinned==1.0\n", encoding="utf-8")
    (source / "README.md").write_text("practice", encoding="utf-8")
    subprocess.run(["git", "-C", str(source), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(source), "-c", "user.name=t", "-c", "user.email=t@x", "commit", "-qm", "start"], check=True)

    class Response:
        def __init__(self, body=None):
            self.body = body or {"saved": True}
        def raise_for_status(self):
            pass
        def json(self):
            return self.body

    class Client:
        def __init__(self, **_kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            pass
        def put(self, url, json):
            events.append(("put", url))
            return Response()
        def post(self, url):
            events.append(("post", url))
            return Response({"run_id": "ordered"})

    monkeypatch.setattr(run_card, "install_practice_requirements",
                        lambda repo: events.append(("install", repo / "setup/requirements.txt")))
    monkeypatch.setattr(run_card.httpx, "Client", Client)
    assert run_card.main([str(card), "--home", str(tmp_path / "home"), "--source", str(source)]) == 0
    capsys.readouterr()

    assert events[0] == ("install", tmp_path / "home/workspaces/self-feature/setup/requirements.txt")
    assert [event[0] for event in events] == ["install", "put", "put", "post"]
