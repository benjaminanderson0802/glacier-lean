import os
import textwrap
from datetime import datetime, timedelta, timezone

from conftest import Server, env


WORKER_PLUGIN = textwrap.dedent('''
    NODE = {
        "catalog": {"type": "cost-worker", "label": "Cost worker", "description": "Records sample usage.", "worker": True,
                    "fields": [], "branches": None},
        "run": lambda ctx: {"state": "done", "output": "ok", "exit_code": 0,
                            "usage": {"model": "small-model", "route": "local/test", "tokens_in": 11,
                                      "tokens_out": 7, "cost_usd": 0.0}},
    }
''')


def test_costs_match_real_plugin_run_and_filter_by_days(tmp_path, monkeypatch):
    plugin_dir = tmp_path / "plugins"
    (plugin_dir / "nodes").mkdir(parents=True)
    (plugin_dir / "nodes" / "cost_worker.py").write_text(WORKER_PLUGIN)
    monkeypatch.setenv("GLACIER_PLUGIN_DIRS", str(plugin_dir))
    monkeypatch.setenv("GLACIER_PAID_CAP_USD", "12.5")
    home = tmp_path / "home"
    home.mkdir()
    server = Server(home).start()
    try:
        e = env("costs", [("work", "cost-worker", {})], [])
        server.put("/api/environments/costs", e)
        run = server.wait_run(server.post("/api/environments/costs/run")["run_id"])
        assert run["status"] == "done"

        costs = server.get("/api/costs", params={"env_id": "costs", "days": 30})
        assert costs == {
            "total_usd": 0.0,
            "by_route": [{"route": "local/test", "runs": 1, "steps": 1, "tokens_in": 11,
                          "tokens_out": 7, "cost_usd": 0.0}],
            "by_model": [{"model": "small-model", "runs": 1, "steps": 1, "tokens_in": 11,
                          "tokens_out": 7, "cost_usd": 0.0}],
            "local_share": 1.0,
            "paid_cap_usd": 12.5,
        }

        # Age this real run beyond the requested window; it must no longer contribute.
        import sqlite3
        db = sqlite3.connect(home / "glacier.sqlite")
        old = (datetime.now(timezone.utc) - timedelta(days=45)).isoformat(timespec="seconds")
        db.execute("UPDATE glacier_runs SET started_at=? WHERE run_id=?", (old, run["run_id"]))
        db.commit()
        db.close()
        recent = server.get("/api/costs", params={"env_id": "costs", "days": 30})
        assert recent["total_usd"] == 0
        assert recent["by_route"] == [] and recent["by_model"] == [] and recent["local_share"] == 0
    finally:
        server.stop()


def test_costs_empty_database_returns_zeros(server):
    assert server.get("/api/costs") == {
        "total_usd": 0.0, "by_route": [], "by_model": [], "local_share": 0.0, "paid_cap_usd": 0.0
    }
