"""Verification core: work counts as done only when an independent check passes (P-VERIFY, rules I-03, I-04, I-11, I-15)."""
import os, json, time
import httpx
from conftest import Server, env


def flow(fid, nodes, edges, acceptance=None, goal=None):
    e = env(fid, nodes, edges)
    if acceptance is not None:
        e["acceptance"] = acceptance
    if goal:
        e["goal"] = goal
    return e


def ws(home, fid):
    return os.path.join(str(home), "workspaces", fid)


def test_goal_without_a_check_cannot_start(server):
    server.put("/api/environments/g0", flow("g0", [("c", "command", {"cmd": "echo hi"})], [], goal="Write a greeting"))
    r = httpx.post(server.url + "/api/environments/g0/run", timeout=30)
    assert r.status_code == 400 and "check" in r.json()["detail"].lower()


def test_unknown_check_kind_rejected_on_save(server):
    r = httpx.put(server.url + "/api/environments/bad", json=flow("bad", [("c", "command", {"cmd": "true"})], [], acceptance=[{"kind": "vibes"}]), timeout=30)
    assert r.status_code == 400


def test_command_check_pass_marks_run_verified(server):
    d = ws(server.home, "g1")
    server.put("/api/environments/g1", flow("g1", [("c", "command", {"cmd": f"mkdir -p {d} && echo hello > {d}/out.txt"})], [],
                                             acceptance=[{"kind": "command", "cmd": "grep -q hello out.txt"}], goal="Write hello to out.txt"))
    run = server.wait_run(server.post("/api/environments/g1/run")["run_id"])
    assert run["status"] == "done" and run["verified"] is True, run
    assert run["verification"][0]["passed"] is True


def test_failed_check_means_not_done(server):
    d = ws(server.home, "g2")
    server.put("/api/environments/g2", flow("g2", [("c", "command", {"cmd": f"mkdir -p {d} && echo bye > {d}/out.txt; echo all done"})], [],
                                             acceptance=[{"kind": "command", "cmd": "grep -q hello out.txt"}], goal="Write hello"))
    run = server.wait_run(server.post("/api/environments/g2/run")["run_id"])
    assert run["status"] == "failed" and run["verified"] is False, run
    assert run["verification"][0]["passed"] is False and run["verification"][0]["evidence"]


def test_worker_cannot_weaken_the_check(server):
    """The worker rewrites the check script to always pass; the verifier uses the saved original and the run fails."""
    d = ws(server.home, "g3")
    cheat = f"mkdir -p {d} && printf 'exit 0' > {d}/check.sh && echo finished"
    server.put("/api/environments/g3", flow("g3", [("c", "command", {"cmd": cheat})], [],
                                             acceptance=[{"kind": "command", "cmd": "sh check.sh", "files": {"check.sh": "grep -q hello out.txt"}}],
                                             goal="Write hello to out.txt"))
    run = server.wait_run(server.post("/api/environments/g3/run")["run_id"])
    assert run["status"] == "failed" and run["verified"] is False, run
    assert "changed check.sh" in run["verification"][0]["evidence"] and "not accepted" in run["verification"][0]["evidence"]
    assert open(os.path.join(d, "check.sh")).read() == "exit 0"  # the worker's folder is left as the worker left it


def test_schema_check(server):
    d = ws(server.home, "g4")
    server.put("/api/environments/g4", flow("g4", [("c", "command", {"cmd": f"mkdir -p {d} && echo '{{\"total\": 3}}' > {d}/r.json"})], [],
               acceptance=[{"kind": "schema", "file": "r.json", "schema": {"type": "object", "required": ["total", "items"]}}], goal="Report"))
    run = server.wait_run(server.post("/api/environments/g4/run")["run_id"])
    assert run["verified"] is False and "items" in run["verification"][0]["evidence"], run


def test_human_check_waits_for_owner(server):
    server.put("/api/environments/g5", flow("g5", [("c", "command", {"cmd": "echo report ready"})], [],
               acceptance=[{"kind": "human", "question": "Does the report look right?"}], goal="Report"))
    rid = server.post("/api/environments/g5/run")["run_id"]
    run = server.wait_run(rid, ("waiting",))
    assert run["waiting_on"] == "check-0" and run["waiting_prompt"] == "Does the report look right?"
    server.post(f"/api/runs/{rid}/approve", {"node_id": "check-0", "approved": True})
    run = server.wait_run(rid)
    assert run["status"] == "done" and run["verified"] is True


def test_rubric_check_uses_separate_judge(tmp_path, monkeypatch):
    from test_core import _fake_ollama
    url, seen, hs = _fake_ollama(lambda prompt: "pass" if "Paris" in prompt else "fail")
    monkeypatch.setenv("GLACIER_OLLAMA_URL", url)
    s = Server(tmp_path).start()
    try:
        s.put("/api/environments/g6", flow("g6", [("c", "command", {"cmd": "echo The capital of France is Paris"})], [],
              acceptance=[{"kind": "rubric", "rubric": "Names the correct capital of France", "engine": "local"}], goal="Answer"))
        run = s.wait_run(s.post("/api/environments/g6/run")["run_id"])
        assert run["verified"] is True, run
        assert "Names the correct capital" in seen[0]["messages"][0]["content"]
    finally:
        s.stop(); hs.shutdown()


def test_stuck_repair_loop_stops_and_files_a_claim(server):
    """Same failure twice in a row = stuck signal: the loop stops and a claim is filed (rules I-11, I-15)."""
    e = flow("stuck", [("c", "command", {"cmd": "echo 'ImportError: no module named zap'; exit 3"}),
                       ("k", "check", {"expr": "exit_code == 0"}), ("n", "note", {"path": "runs/{run}.md", "template": "ok"})],
             [("c", "k", ""), ("k", "n", "yes"), ("k", "c", "no")])
    server.put("/api/environments/stuck", e)
    run = server.wait_run(server.post("/api/environments/stuck/run")["run_id"])
    assert run["status"] == "failed", run
    # research routes it to the debugger; the debugger's attempt cannot fix this, the proof re-run stays stuck,
    # so the claim is escalated to the owner (and the re-run does not start yet another repair cycle)
    deadline = time.time() + 90
    while time.time() < deadline:
        claims = server.get("/api/claims")
        if claims and claims[0]["status"] == "proposed":
            break
        time.sleep(0.5)
    assert len(claims) == 1 and claims[0]["kind"] == "bug" and claims[0]["status"] == "proposed", claims
    body = server.get(f"/api/claims/{claims[0]['id']}")["body"]
    assert "Specialist attempt (debugger)" in body and "Escalated" in body
    c = server.get(f"/api/claims/{claims[0]['id']}")
    assert "no module named zap" in c["body"] and c["meta"]["attempts_made"] == 2 and c["meta"]["run_id"] == run["run_id"]


def test_claims_api_and_owner_decision(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_AUTO_RESEARCH", "0")  # keep the claim still while the owner decides
    server = Server(tmp_path).start()
    try:
        _claims_api_and_decision(server)
    finally:
        server.stop()


def _claims_api_and_decision(server):
    r = server.post("/api/claims", {"kind": "capability_gap", "summary": "Need a PDF table reader",
                                     "evidence": "MarkItDown loses table layout"})
    cid = r["id"]
    assert r["path"].startswith("claims/") and r["path"].endswith(".md")
    assert [c["id"] for c in server.get("/api/claims", params={"status": "filed"})] == [cid]
    assert server.post(f"/api/claims/{cid}/decision", {"action": "reject"})["status"] == "closed"
    c = server.get(f"/api/claims/{cid}")
    assert c["meta"]["status"] == "closed" and "rejected" in c["body"].lower()
    bad = httpx.post(server.url + "/api/claims", json={"kind": "whatever", "summary": "x", "evidence": "y"}, timeout=30)
    assert bad.status_code == 400


def test_tampering_fails_even_when_the_work_is_right(server):
    """Correct work + an edited check file is still rejected: the rule against touching your own check is absolute."""
    d = ws(server.home, "g7")
    cmd = f"mkdir -p {d} && echo hello > {d}/out.txt && printf 'exit 0' > {d}/check.sh && echo done"
    server.put("/api/environments/g7", flow("g7", [("c", "command", {"cmd": cmd})], [],
                                             acceptance=[{"kind": "command", "cmd": "sh check.sh", "files": {"check.sh": "grep -q hello out.txt"}}],
                                             goal="Write hello"))
    run = server.wait_run(server.post("/api/environments/g7/run")["run_id"])
    assert run["verified"] is False and "not accepted" in run["verification"][0]["evidence"], run
