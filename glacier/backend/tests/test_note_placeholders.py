import re
import time

from conftest import env


def test_note_saves_previous_output_under_a_dated_path(server):
    e = env("dated", [("c", "command", {"cmd": "echo proposal-body-123"}),
                      ("n", "note", {"path": "proposals/check-{date}.md",
                                     "template": "Proposal\n\n{prev_output}\n\nStep results: {summary}"})],
            [("c", "n", "")])
    server.put("/api/environments/dated", e)
    run_id = server.post("/api/environments/dated/run")["run_id"]
    run = server.wait_run(run_id)
    assert run["status"] == "done"
    today = time.strftime("%Y-%m-%d", time.gmtime())
    path = f"proposals/check-{today}.md"
    assert path in server.get("/api/vault/notes")
    body = server.get("/api/vault/note", params={"path": path})["body"]
    assert "proposal-body-123" in body and "Step results: c: done" in body
    assert not re.search(r"\{(date|prev_output)\}", body)


def test_existing_note_templates_are_unchanged(server):
    e = env("plain", [("c", "command", {"cmd": "echo hi"}),
                      ("n", "note", {"path": "runs/{env}-{run}.md", "template": "Run {run} of {env}: {summary}"})],
            [("c", "n", "")])
    server.put("/api/environments/plain", e)
    run_id = server.post("/api/environments/plain/run")["run_id"]
    server.wait_run(run_id)
    body = server.get("/api/vault/note", params={"path": f"runs/plain-{run_id}.md"})["body"]
    assert body.startswith(f"Run {run_id} of plain: c: done")
