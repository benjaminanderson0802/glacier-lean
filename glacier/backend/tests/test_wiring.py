"""Acceptance tests for secrets, cumulative usage and MCP claim filing."""
import json
import os
import sys
import textwrap

import keyring
from conftest import Server, env


class MemoryKeyring(keyring.backend.KeyringBackend):
    priority = 1

    def __init__(self):
        self.values = {}

    def get_password(self, service, username):
        return self.values.get((service, username))

    def set_password(self, service, username, password):
        self.values[(service, username)] = password

    def delete_password(self, service, username):
        del self.values[(service, username)]


def _start_with_memory_keyring(server, home, monkeypatch):
    """Load a test-only in-memory keyring in the real uvicorn subprocess."""
    hook = home / "keyring_hook"
    hook.mkdir(exist_ok=True)
    (hook / "sitecustomize.py").write_text(textwrap.dedent(f'''\
        import json, keyring
        class MemoryKeyring(keyring.backend.KeyringBackend):
            priority = 1
            path = {str(home / "test-keyring.json")!r}
            def values(self):
                try:
                    with open(self.path) as handle: return json.load(handle)
                except FileNotFoundError: return {{}}
            def get_password(self, service, username): return self.values().get(service + ":" + username)
            def set_password(self, service, username, password):
                values = self.values(); values[service + ":" + username] = password
                with open(self.path, "w") as handle: json.dump(values, handle)
            def delete_password(self, service, username):
                values = self.values(); values.pop(service + ":" + username, None)
                with open(self.path, "w") as handle: json.dump(values, handle)
        keyring.set_keyring(MemoryKeyring())
    '''))
    monkeypatch.setenv("PYTHONPATH", str(hook) + os.pathsep + os.environ.get("PYTHONPATH", ""))


def test_command_secret_is_redacted_from_run_and_vault(server, monkeypatch):
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    import secrets_store
    monkeypatch.setenv("GLACIER_HOME", server.home)
    home = __import__("pathlib").Path(server.home)
    _start_with_memory_keyring(server, home, monkeypatch)
    server.stop()
    server = Server(server.home)
    server.start()
    raw = "private-token-7654"
    (home / "test-keyring.json").write_text(json.dumps({"Glacier:tok": raw}))
    secrets_store._write_names(["tok"])
    try:
        server.put("/api/environments/secret-flow", env("secret-flow", [
            ("print", "command", {"cmd": "printf '%s' '{secret:tok}'"}),
        ], []))
        run_id = server.post("/api/environments/secret-flow/run")["run_id"]
        run = server.wait_run(run_id)
        assert run["status"] == "done"
        payload = json.dumps(server.get(f"/api/runs/{run_id}"))
        assert "[secret tok]" in payload
        assert raw not in payload
        for root, _, files in os.walk(os.path.join(server.home, "vault")):
            for name in files:
                assert raw not in open(os.path.join(root, name), errors="ignore").read()
    finally:
        server.stop()


def test_unknown_command_secret_fails_with_plain_message(server, monkeypatch):
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    monkeypatch.setenv("GLACIER_HOME", server.home)
    home = __import__("pathlib").Path(server.home)
    _start_with_memory_keyring(server, home, monkeypatch)
    server.stop()
    server = Server(server.home)
    server.start()
    try:
        server.put("/api/environments/missing-secret", env("missing-secret", [
            ("print", "command", {"cmd": "printf '{secret:missing}'"}),
        ], []))
        run_id = server.post("/api/environments/missing-secret/run")["run_id"]
        run = server.wait_run(run_id)
        assert run["status"] == "failed"
        assert "This step uses a secret named missing that isn't saved yet. Add it in Settings > Secrets." in run["outputs"]["print"]
    finally:
        server.stop()


def test_loop_usage_accumulates_each_execution(tmp_path, monkeypatch):
    plugin_dir = tmp_path / "plugins"
    (plugin_dir / "nodes").mkdir(parents=True)
    (plugin_dir / "nodes" / "usage_worker.py").write_text(textwrap.dedent('''
        NODE = {"catalog": {"type": "usage-worker", "label": "Usage worker", "description": "Reports usage.",
                "worker": True, "fields": [], "branches": None},
               "run": lambda ctx: {"state": "done", "output": "ok", "exit_code": 0,
                   "usage": {"model": "last-model", "route": "local/test", "tokens_in": 3,
                             "tokens_out": 4, "cost_usd": 0.25}}}
    '''))
    monkeypatch.setenv("GLACIER_PLUGIN_DIRS", str(plugin_dir))
    home = tmp_path / "home"
    home.mkdir()
    s = Server(home).start()
    try:
        flow = env("usage-loop", [("loop", "loop", {"times": "3"}), ("worker", "usage-worker", {})],
                   [("loop", "worker", "again"), ("worker", "loop", "")])
        flow["edges"] = [
            {"id": "e0", "source": "loop", "target": "worker", "label": "again"},
            {"id": "e1", "source": "worker", "target": "loop", "label": ""},
        ]
        s.put("/api/environments/usage-loop", flow)
        run_id = s.post("/api/environments/usage-loop/run")["run_id"]
        run = s.wait_run(run_id)
        assert run["status"] == "done"
        assert s.get(f"/api/runs/{run_id}")["usage"]["worker"] == {
            "model": "last-model", "route": "local/test", "tokens_in": 9,
            "tokens_out": 12, "cost_usd": 0.75,
        }
    finally:
        s.stop()


def test_mcp_file_claim_validates_worker_and_kind(tmp_path):
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    import vault
    import claims
    import mem_server
    vault.init(str(tmp_path / "vault"))
    claim_id = mem_server.file_claim("bug", "bad connection", "could not connect", "worker:agent", "run-123")
    claim_id = json.loads(claim_id)["id"]
    assert claims.get_claim(claim_id)["meta"]["filed_by"] == "worker:agent"
    for kind, author in (("invented", "worker:agent"), ("bug", "owner")):
        try:
            mem_server.file_claim(kind, "bad input", "evidence", author, "run-123")
        except ValueError as exc:
            assert str(exc)
        else:
            raise AssertionError("invalid claim kind or author was accepted")


def test_codex_secret_placeholder_is_rejected_without_resolution(server, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", server.home)
    server.put("/api/environments/codex-secret", env("codex-secret", [
        ("ask", "codex", {"prompt": "use {secret:tok}"}),
    ], []))
    run_id = server.post("/api/environments/codex-secret/run")["run_id"]
    run = server.wait_run(run_id)
    assert run["status"] == "failed"
    assert run["outputs"]["ask"] == "error: Secrets can't be sent to an AI model. Use the secret in a command step instead."


def test_node_output_is_hidden_when_keyring_cannot_redact(tmp_path, monkeypatch):
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    import store
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    store.init(str(tmp_path / "db.sqlite"))
    store.create_run("run1", "flow", {"nodes": [{"id": "node"}]})
    import secrets_store
    def broken_redact(text):
        raise RuntimeError("keyring unavailable")
    monkeypatch.setattr(secrets_store, "redact", broken_redact)
    store.set_node("run1", "flow", "node", "done", "may contain a secret")
    assert store.get_run("run1")["outputs"]["node"] == "[output hidden: secrets could not be checked]"


def test_folder_backup_commands_use_absolute_glacier_home_in_real_run(tmp_path, monkeypatch):
    monkeypatch.delenv("GLACIER_HOME", raising=False)
    monkeypatch.setenv("GLACIER_PLUGIN_DIRS", "")
    home = tmp_path / "home"
    home.mkdir()
    s = Server(home).start()
    try:
        template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "templates", "tpl-folder-backup.json"))
        template = json.loads(open(template_path, encoding="utf-8").read())
        for node in template["nodes"]:
            if node["type"] == "schedule":
                continue
            node["position"] = {"x": 0, "y": 0}
        s.put("/api/environments/backup", template)
        run_id = s.post("/api/environments/backup/run")["run_id"]
        run = s.wait_run(run_id)
        assert run["status"] == "done", run
        workspace = home / "workspaces" / "backup"
        backups = list((home / "backups" / "tpl-folder-backup").glob("*") )
        assert backups and backups[0].is_dir()
        assert not (workspace / "backups").exists()
    finally:
        s.stop()
