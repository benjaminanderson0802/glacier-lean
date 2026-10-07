import httpx

from conftest import env


def test_rerun_starts_the_flow_again_and_notes_it_on_the_claim(server):
    server.put("/api/environments/cr", env("cr", [("c", "command", {"cmd": "echo hello"})], []))
    first = server.post("/api/environments/cr/run")["run_id"]
    server.wait_run(first)
    cid = server.post("/api/claims", {"kind": "bug", "summary": "Step c needs checking", "evidence": "x", "run_id": first})["id"]
    out = server.post(f"/api/claims/{cid}/rerun")
    assert out["env_id"] == "cr" and out["run_id"] != first
    again = server.wait_run(out["run_id"])
    assert again["status"] == "done"
    body = server.get(f"/api/claims/{cid}")["body"]
    assert f"ran the flow again to check: run {out['run_id']}" in body


def test_rerun_needs_a_run(server):
    cid = server.post("/api/claims", {"kind": "bug", "summary": "No run here", "evidence": "x"})["id"]
    r = httpx.post(server.url + f"/api/claims/{cid}/rerun", timeout=10)
    assert r.status_code == 400 and "nothing to run again" in r.json()["detail"]
