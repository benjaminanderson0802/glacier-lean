"""Step and route plug-ins: new step types and API routes live in their own files (parallel builders never edit shared files)."""
import os, textwrap
import httpx
from conftest import Server, env

NODE_PLUGIN = textwrap.dedent('''
    NODE = {
        "catalog": {"type": "shout", "label": "Shout", "description": "Upper-cases the previous output.", "worker": True,
                    "fields": [{"key": "suffix", "label": "Suffix", "placeholder": "!", "default": "!"}], "branches": None},
        "run": lambda ctx: {"state": "done", "output": (ctx["prev"] or {}).get("output", "").upper().strip() + ctx["config"].get("suffix", ""),
                            "exit_code": 0,
                            "usage": {"model": "tiny-test-model", "route": "local/test", "tokens_in": 3, "tokens_out": 2, "cost_usd": 0}},
    }
''')
ROUTE_PLUGIN = textwrap.dedent('''
    from fastapi import APIRouter
    router = APIRouter()

    @router.get("/api/hello")
    def hello():
        return {"hello": "plugin"}
''')


def _plugin_dir(tmp_path):
    d = tmp_path / "plugs"
    (d / "nodes").mkdir(parents=True); (d / "routes").mkdir()
    (d / "nodes" / "shout.py").write_text(NODE_PLUGIN)
    (d / "routes" / "hello.py").write_text(ROUTE_PLUGIN)
    return str(d)


def test_step_and_route_plugins(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_PLUGIN_DIRS", _plugin_dir(tmp_path))
    home = tmp_path / "home"; home.mkdir()
    s = Server(home).start()
    try:
        assert "shout" in [t["type"] for t in s.get("/api/node-types")]
        assert s.get("/api/hello") == {"hello": "plugin"}
        e = env("plug", [("c", "command", {"cmd": "echo hi there"}), ("p", "shout", {"suffix": "!!"}),
                         ("k", "check", {"expr": "exit_code == 0"}), ("n", "note", {"path": "runs/{run}.md", "template": "ok"})],
                [("c", "p", ""), ("p", "k", ""), ("k", "n", "yes")])
        s.put("/api/environments/plug", e)
        run = s.wait_run(s.post("/api/environments/plug/run")["run_id"])
        assert run["status"] == "done" and run["outputs"]["p"] == "HI THERE!!" and run["node_states"]["n"] == "done", run
        assert run["usage"]["p"] == {"model": "tiny-test-model", "route": "local/test", "tokens_in": 3, "tokens_out": 2, "cost_usd": 0.0}
    finally:
        s.stop()


def test_codex_step_records_route_and_zero_cost(server):
    e = env("cx-usage", [("x", "codex", {"prompt": "say hi", "sandbox": "read-only"})], [])
    server.put("/api/environments/cx-usage", e)
    run = server.wait_run(server.post("/api/environments/cx-usage/run")["run_id"])
    u = run["usage"]["x"]
    assert u["route"] == "codex/chatgpt-plan" and u["cost_usd"] == 0.0, u


def test_plugin_cannot_redefine_core_type(tmp_path, monkeypatch):
    d = tmp_path / "bad"; (d / "nodes").mkdir(parents=True)
    (d / "nodes" / "evil.py").write_text('NODE = {"catalog": {"type": "command", "label": "x", "fields": [], "branches": None}, "run": lambda c: {}}')
    monkeypatch.setenv("GLACIER_PLUGIN_DIRS", str(d))
    home = tmp_path / "home"; home.mkdir()
    s = Server(home)
    try:
        s.start()
        raised = False
    except RuntimeError:
        raised = True
    finally:
        s.stop()
    assert raised and "already defined" in open(os.path.join(str(home), "server.log")).read()
