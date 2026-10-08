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


def test_claim_research_and_rerun_updates_share_the_vault_lock(monkeypatch):
    import claims_research
    import routes.claims as claim_routes
    import vault

    original_lock = vault._lock
    active = False
    seen = []
    writes = []

    class CheckedLock:
        def __enter__(self):
            nonlocal active
            seen.append("enter")
            original_lock.__enter__()
            active = True
            return self

        def __exit__(self, *args):
            nonlocal active
            active = False
            seen.append("exit")
            return original_lock.__exit__(*args)

    monkeypatch.setattr(vault, "_lock", CheckedLock())
    monkeypatch.setattr(claims_research, "_record_and_route_locked", lambda *args: {"status": "routed"})
    claims_research.record_and_route("claim-1234", [], "")
    claim = {"meta": {"run_id": "old-run"}, "body": "## Problem\ncheck\n\n## Resolution\n"}
    monkeypatch.setattr(claim_routes.claims, "get_claim", lambda _cid: claim)
    monkeypatch.setattr(claim_routes.store, "get_run", lambda _rid: {"env_id": "flow"})

    def start_run(_env_id, _settings):
        assert active
        return "new-run"

    def write_note(_path, rendered, **_kwargs):
        assert active
        writes.append(rendered)

    monkeypatch.setattr(claim_routes.runner, "start_run", start_run)
    monkeypatch.setattr(claim_routes.vault, "write_note", write_note)
    monkeypatch.setattr(claim_routes.store.broadcaster, "publish", lambda _event: None)
    assert claim_routes.rerun_claim("claim-1234") == {"run_id": "new-run", "env_id": "flow"}
    assert "new-run" in writes[-1]
    assert seen.count("enter") == 2 and seen.count("exit") == 2


def test_rerun_resolution_survives_automatic_workflow_write(monkeypatch):
    import claims_specialist
    import claims
    import store
    import vault

    claim = {"meta": {"run_id": "old-run"}, "body": "## Problem\ncheck\n\n## Resolution\n"}
    saved = []
    monkeypatch.setattr(claims, "get_claim", lambda _cid: claim)
    monkeypatch.setattr(claims, "_now", lambda: "now")
    monkeypatch.setattr(store, "get_run", lambda _rid: {"env_id": "cr"})
    monkeypatch.setattr(claims_specialist.workspaces, "base", lambda *_args: "/tmp/cr")
    monkeypatch.setattr(claims_specialist.os, "makedirs", lambda *_args, **_kwargs: None)

    def write_note(_path, rendered, **_kwargs):
        saved.append(rendered)
        _, body = claims._parse(rendered)
        claim["body"] = body

    monkeypatch.setattr(vault, "write_note", write_note)
    monkeypatch.setattr(store.broadcaster, "publish", lambda _event: None)

    # Reproduce the Windows CI ordering: the owner records the rerun, then
    # automatic research/fix completes and records its proof.
    claim["body"] = claims.append_resolution(
        claim["body"], "- now Owner ran the flow again to check: run new-run."
    )
    claims_specialist.close_claim("claim-1234", "new-run", "done", None)

    body = claim["body"]
    assert "Owner ran the flow again to check: run new-run" in body
    assert "Fixed and proven: re-run new-run finished" in body
    assert body.count("## Resolution") == 1


def test_specialist_echoed_prompt_does_not_duplicate_claim_sections_or_drop_rerun(monkeypatch):
    import claims_specialist
    import claims
    import store
    import vault

    original = "## Problem\nStep c needs checking\n\n## Evidence\nx\n\n## Research\nNo similar past fix found.\n\n## Resolution\n"
    claim = {"meta": {"run_id": "old-run", "assigned_to": "fixer"}, "body": original}
    monkeypatch.setattr(claims, "get_claim", lambda _cid: claim)
    monkeypatch.setattr(claims, "_now", lambda: "now")
    monkeypatch.setattr(store, "get_run", lambda _rid: {"env_id": "cr"})
    monkeypatch.setattr(claims_specialist.workspaces, "base", lambda *_args: "/tmp/cr")
    monkeypatch.setattr(claims_specialist.os, "makedirs", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(claims_specialist, "_prompt", lambda _meta, body: "prompt\n" + body)
    echoed = "The claim was:\n" + original + " [sandbox=workspace-write cwd=cr model=None]"
    monkeypatch.setattr(claims_specialist, "run_specialist", lambda *_args: (0, echoed))

    def write_note(_path, rendered, **_kwargs):
        _, claim["body"] = claims._parse(rendered)

    monkeypatch.setattr(vault, "write_note", write_note)
    monkeypatch.setattr(store.broadcaster, "publish", lambda _event: None)
    claim["body"] = claims.append_resolution(
        claim["body"], "- now Owner ran the flow again to check: run new-run."
    )

    claims_specialist.specialist_attempt("claim-1234")
    body = claim["body"]
    assert body.count("## Problem") == 1
    assert body.count("## Evidence") == 1
    assert body.count("## Research") == 1
    assert body.count("## Resolution") == 1
    assert "Owner ran the flow again to check: run new-run" in body
    assert "Step c needs checking" not in body.split("## Resolution", 1)[1]
    assert "[sandbox=workspace-write" not in body
