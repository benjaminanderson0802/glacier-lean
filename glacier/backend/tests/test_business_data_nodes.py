"""Acceptance checks for the local business data nodes (written before their runner code)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nodes._business_data import CSV_NODE, DELAY_NODE, JSON_NODE, TABLE_NODE  # noqa: E402
from nodes.structured_ai import NODE as STRUCTURED_AI_NODE  # noqa: E402


def ctx(tmp_path, config, previous=None):
    return {
        "config": config,
        "home": str(tmp_path / "glacier-home"),
        "workspace": str(tmp_path / "workspace"),
        "prev": {"output": previous if isinstance(previous, str) else json.dumps(previous)} if previous is not None else None,
    }


def test_json_set_fields_and_filter_are_structured_and_repeatable(tmp_path):
    result = JSON_NODE["run"](ctx(tmp_path, {
        "operation": "set_fields", "fields": '{"status":"ready","total":3}'
    }, {"name": "Ada"}))
    assert json.loads(result["output"]) == {"name": "Ada", "status": "ready", "total": 3}

    result = JSON_NODE["run"](ctx(tmp_path, {
        "operation": "set_fields", "fields": '{"source":"Glacier example"}'
    }, [{"id": 1}, {"id": 2}]))
    assert json.loads(result["output"]) == [
        {"id": 1, "source": "Glacier example"}, {"id": 2, "source": "Glacier example"}
    ]

    result = JSON_NODE["run"](ctx(tmp_path, {
        "operation": "filter", "field": "active", "equals": "true"
    }, [{"id": 1, "active": True}, {"id": 2, "active": False}]))
    assert json.loads(result["output"]) == [{"id": 1, "active": True}]


def test_json_split_and_merge_accept_common_automation_shapes(tmp_path):
    split = JSON_NODE["run"](ctx(tmp_path, {"operation": "split"}, {"items": [1, 2]}))
    assert json.loads(split["output"]) == [1, 2]
    merged = JSON_NODE["run"](ctx(tmp_path, {"operation": "merge"}, {"a": 1}))
    assert json.loads(merged["output"]) == {"a": 1}


def test_table_upsert_query_and_dedupe_use_rebuildable_local_sqlite(tmp_path):
    first = TABLE_NODE["run"](ctx(tmp_path, {
        "table": "customers", "operation": "upsert", "key": "email",
        "record": '{"email":"ada@example.test","name":"Ada"}'
    }))
    second = TABLE_NODE["run"](ctx(tmp_path, {
        "table": "customers", "operation": "upsert", "key": "email",
        "record": '{"email":"ada@example.test","name":"Ada Lovelace"}'
    }))
    assert first["state"] == second["state"] == "done"
    home = tmp_path / "glacier-home"
    source = home / "tables" / "customers.json"
    assert json.loads(source.read_text(encoding="utf-8")) == [
        {"email": "ada@example.test", "name": "Ada Lovelace"}
    ]
    (home / "tables.sqlite").unlink()
    rows = TABLE_NODE["run"](ctx(tmp_path, {"table": "customers", "operation": "query"}))
    assert json.loads(rows["output"]) == [{"email": "ada@example.test", "name": "Ada Lovelace"}]
    assert (home / "tables.sqlite").is_file()
    deduped = TABLE_NODE["run"](ctx(tmp_path, {
        "table": "customers", "operation": "dedupe", "key": "email"
    }))
    assert json.loads(deduped["output"])["removed"] == 0


def test_csv_read_write_stays_inside_flow_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    writer = ctx(tmp_path, {
        "operation": "write", "path": "out.csv", "data": "[{\"id\":1,\"name\":\"Ada\"}]"
    }, None)
    writer["workspace"] = str(workspace)
    result = CSV_NODE["run"](writer)
    assert result["state"] == "done"
    assert (workspace / "out.csv").read_text(encoding="utf-8").splitlines() == ["id,name", "1,Ada"]

    reader = ctx(tmp_path, {"operation": "read", "path": "out.csv"})
    reader["workspace"] = str(workspace)
    assert json.loads(CSV_NODE["run"](reader)["output"]) == [{"id": "1", "name": "Ada"}]

    reader["config"]["path"] = "../outside.csv"
    assert CSV_NODE["run"](reader)["state"] == "failed"

    single = ctx(tmp_path, {"operation": "write", "path": "one-row.csv"}, {"id": 2, "name": "Grace"})
    single["workspace"] = str(workspace)
    assert CSV_NODE["run"](single)["state"] == "done"
    assert (workspace / "one-row.csv").read_text(encoding="utf-8").splitlines() == ["id,name", "2,Grace"]


def test_delay_caps_wait_and_returns_previous_output(tmp_path, monkeypatch):
    import nodes._business_data as business_data
    waited = []
    monkeypatch.setattr(business_data.time, "sleep", waited.append)
    result = DELAY_NODE["run"](ctx(tmp_path, {"seconds": "2"}, "ready"))
    assert waited == [2]
    assert result["output"] == "ready"


def test_structured_ai_uses_gateway_and_checks_json_schema(tmp_path, monkeypatch):
    import gateway
    monkeypatch.setattr(gateway, "complete", lambda ctx, routes=None, timeout=None: {
        "state": "done", "exit_code": 0, "output": '{"ok":true}',
        "usage": {"route": "gateway/local", "model": "local", "tokens_in": 2, "tokens_out": 2, "cost_usd": 0},
    })
    result = STRUCTURED_AI_NODE["run"](ctx(tmp_path, {
        "prompt": "Check the item", "schema": '{"type":"object","required":["ok"],"properties":{"ok":{"type":"boolean"}}}'
    }))
    assert json.loads(result["output"]) == {"ok": True}
    assert result["usage"]["route"] == "gateway/local"

    monkeypatch.setattr(gateway, "complete", lambda *args, **kwargs: {"state": "done", "exit_code": 0, "output": '{"ok":"yes"}'})
    assert STRUCTURED_AI_NODE["run"](ctx(tmp_path, {
        "prompt": "Check the item", "schema": '{"type":"object","properties":{"ok":{"type":"boolean"}}}'
    }))["state"] == "failed"


def test_structured_ai_can_use_the_owners_codex_cli_route(tmp_path, monkeypatch):
    import runner
    calls = []
    monkeypatch.setattr(runner, "run_codex", lambda env_id, run_id, node_id, config, previous, timeout, workspace: (
        calls.append((env_id, run_id, node_id, timeout, workspace, config["prompt"])) or
        {"state": "done", "exit_code": 0, "output": 'codex exit 0\n{"ok":true}',
         "usage": {"route": "codex/chatgpt-plan", "model": "default", "tokens_in": 1, "tokens_out": 1, "cost_usd": 0}}
    ))
    result = STRUCTURED_AI_NODE["run"](ctx(tmp_path, {
        "engine": "codex", "prompt": "Check the item", "schema": '{"type":"object","required":["ok"],"properties":{"ok":{"type":"boolean"}}}',
        "timeout": "17",
    }))
    assert result["state"] == "done"
    assert json.loads(result["output"]) == {"ok": True}
    assert calls[0][:4] == ("", "", "", 17)
    assert "Return only JSON" in calls[0][-1]
