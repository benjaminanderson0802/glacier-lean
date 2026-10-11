"""Acceptance check for opt-in retries on retry-safe step plug-ins."""
import textwrap

from conftest import Server, env


def test_retry_safe_plugin_retries_with_step_policy(tmp_path, monkeypatch):
    plugin_root = tmp_path / "plugins"
    (plugin_root / "nodes").mkdir(parents=True)
    counter = tmp_path / "attempts.txt"
    source = textwrap.dedent(f'''\
        from pathlib import Path
        counter = Path({str(counter)!r})
        def run(ctx):
            attempts = int(counter.read_text() if counter.exists() else "0") + 1
            counter.write_text(str(attempts))
            if attempts < 2:
                return {{"state": "failed", "exit_code": 1, "output": "temporary problem"}}
            return {{"state": "done", "exit_code": 0, "output": "recovered"}}
        NODE = {{"catalog": {{"type": "retry_example", "label": "Retry example", "description": "test",
            "worker": True, "retry_safe": True, "fields": [
              {{"key": "retries", "label": "Retries if it fails", "default": "0"}}], "branches": None}}, "run": run}}
    ''')
    (plugin_root / "nodes" / "retry_example.py").write_text(source, encoding="utf-8")
    monkeypatch.setenv("GLACIER_PLUGIN_DIRS", str(plugin_root))
    home = tmp_path / "home"
    home.mkdir()
    server = Server(home).start()
    try:
        catalog = {item["type"]: item for item in server.get("/api/node-types")}
        assert catalog["retry_example"]["fields"][-1]["key"] == "retries"
        flow = env("retry-flow", [("step", "retry_example", {"retries": "1"})], [])
        server.put("/api/environments/retry-flow", flow)
        run = server.wait_run(server.post("/api/environments/retry-flow/run")["run_id"])
        assert run["status"] == "done", run
        assert run["outputs"]["step"] == "[attempt 2 of 2]\nrecovered"
        assert counter.read_text(encoding="utf-8") == "2"
    finally:
        server.stop()
