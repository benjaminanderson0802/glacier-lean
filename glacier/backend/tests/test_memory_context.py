"""AI steps get relevant notes from memory added to their task (and can opt out)."""
from conftest import env


def test_codex_task_includes_relevant_notes(server):
    server.put("/api/environments/mem", env("mem", [("n", "note", {"path": "notes/deploy-checklist.md",
                                                                 "template": "Deploy checklist: run migrations before restarting the API"})], []))
    server.wait_run(server.post("/api/environments/mem/run")["run_id"])
    server.put("/api/environments/cx", env("cx", [("x", "codex", {"prompt": "Write the deploy steps for the API", "sandbox": "read-only"})], []))
    run = server.wait_run(server.post("/api/environments/cx/run")["run_id"])
    out = run["outputs"]["x"]  # the fake Codex echoes the task it received
    assert "Relevant notes:" in out and "run migrations before restarting" in out, out


def test_memory_can_be_switched_off_per_step(server):
    server.put("/api/environments/mem2", env("mem2", [("n", "note", {"path": "notes/deploy.md", "template": "deploy secret sauce"})], []))
    server.wait_run(server.post("/api/environments/mem2/run")["run_id"])
    server.put("/api/environments/cx2", env("cx2", [("x", "codex", {"prompt": "Write the deploy steps", "sandbox": "read-only", "use_memory": "no"})], []))
    run = server.wait_run(server.post("/api/environments/cx2/run")["run_id"])
    assert "Relevant notes:" not in run["outputs"]["x"]
