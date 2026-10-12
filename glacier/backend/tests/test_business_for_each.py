"""Acceptance check for bounded per-item loops over JSON arrays."""
import json

from conftest import env


def test_for_each_runs_each_item_and_returns_to_the_done_branch(server):
    flow = env("for-each-items", [
        ("source", "json_transform", {"operation": "merge", "data": '[{"id":"one","name":"Ada"},{"id":"two","name":"Grace"}]'}),
        ("each", "for_each", {"max_items": "10"}),
        ("save", "data_table", {"table": "loop_items", "operation": "upsert", "key": "id"}),
        ("rows", "data_table", {"table": "loop_items", "operation": "query"}),
    ], [("source", "each", ""), ("each", "save", "each"), ("save", "each", ""), ("each", "rows", "done")])
    server.put("/api/environments/for-each-items", flow)
    run = server.wait_run(server.post("/api/environments/for-each-items/run")["run_id"])
    assert run["status"] == "done", run
    assert json.loads(run["outputs"]["rows"]) == [
        {"id": "one", "name": "Ada"}, {"id": "two", "name": "Grace"}
    ]
    assert run["node_states"]["each"] == "done"


def test_for_each_refuses_non_list_input(server):
    flow = env("for-each-bad-input", [("each", "for_each", {"max_items": "1"})], [])
    server.put("/api/environments/for-each-bad-input", flow)
    run = server.wait_run(server.post("/api/environments/for-each-bad-input/run")["run_id"])
    assert run["status"] == "failed"
    assert "list" in run["outputs"]["each"].lower()


def test_for_each_caps_the_number_of_items(server):
    flow = env("for-each-item-cap", [
        ("source", "json_transform", {"operation": "merge", "data": '[{"id":1},{"id":2}]'}),
        ("each", "for_each", {"max_items": "1"}),
    ], [("source", "each", "")])
    server.put("/api/environments/for-each-item-cap", flow)
    run = server.wait_run(server.post("/api/environments/for-each-item-cap/run")["run_id"])
    assert run["status"] == "failed"
    assert "limit" in run["outputs"]["each"].lower()
