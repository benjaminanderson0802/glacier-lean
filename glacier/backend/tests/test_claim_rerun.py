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


def test_claim_updates_serialize_read_modify_write_and_preserve_both_writers(monkeypatch):
    import threading
    import claims

    cid = "2026-10-08-interleaved-claim-updates-d96cbd"
    saved = {"text": claims._render({"id": cid}, "## Problem\nx\n\n## Resolution\n")}
    monkeypatch.setattr(claims.vault, "read_note", lambda _path: saved["text"])

    def save_note(_path, text, **_kwargs):
        saved["text"] = text

    monkeypatch.setattr(claims.vault, "write_note", save_note)
    read_done = threading.Event()
    allow_first_write = threading.Event()
    first_thread = {"id": None}
    original_lock = claims.vault._lock

    class PausedLock:
        def __enter__(self):
            original_lock.__enter__()
            if threading.get_ident() == first_thread["id"] and not read_done.is_set():
                read_done.set()
                assert allow_first_write.wait(5)
            return self

        def __exit__(self, *args):
            return original_lock.__exit__(*args)

    monkeypatch.setattr(claims.vault, "_lock", PausedLock())
    errors = []

    def first_writer():
        first_thread["id"] = threading.get_ident()
        try:
            claims.update_claim(cid, lambda meta, body: (meta, claims.append_resolution(body, "first writer")), agent="test")
        except Exception as exc:  # surfaced in the main test thread
            errors.append(exc)

    worker = threading.Thread(target=first_writer)
    worker.start()
    assert read_done.wait(5)

    second_done = threading.Event()

    def second_writer():
        try:
            claims.update_claim(cid, lambda meta, body: (meta, claims.append_resolution(body, "second writer")), agent="test")
        except Exception as exc:
            errors.append(exc)
        finally:
            second_done.set()

    second = threading.Thread(target=second_writer)
    second.start()
    assert not second_done.wait(0.05), "second writer must wait while first holds the vault lock"
    allow_first_write.set()
    worker.join(5)
    second.join(5)
    assert not worker.is_alive() and not second.is_alive()
    assert errors == []
    body = claims.get_claim(cid)["body"]
    assert "first writer" in body
    assert "second writer" in body


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
    monkeypatch.setattr(claims_research.claims, "update_claim", lambda _cid, fn, **_kw: {"meta": fn({}, "")[0]})
    claims_research.record_and_route("claim-1234", [], "")
    claim = {"meta": {"run_id": "old-run"}, "body": "## Problem\ncheck\n\n## Resolution\n"}
    monkeypatch.setattr(claim_routes.claims, "get_claim", lambda _cid: claim)
    def update_claim(_cid, fn, **_kwargs):
        with claim_routes.claims.vault._lock:
            return _mutate_claim(fn, claim, writes)
    monkeypatch.setattr(claim_routes.claims, "update_claim", update_claim)
    monkeypatch.setattr(claim_routes.store, "get_run", lambda _rid: {"env_id": "flow"})

    def start_run(_env_id, _settings):
        assert active
        return "new-run"

    monkeypatch.setattr(claim_routes.runner, "start_run", start_run)
    monkeypatch.setattr(claim_routes.store.broadcaster, "publish", lambda _event: None)
    assert claim_routes.rerun_claim("claim-1234") == {"run_id": "new-run", "env_id": "flow"}
    assert "new-run" in writes[-1]
    assert seen.count("enter") == 1 and seen.count("exit") == 1


def test_rerun_resolution_survives_automatic_workflow_write(monkeypatch):
    import claims_specialist
    import claims
    import store
    claim = {"meta": {"run_id": "old-run"}, "body": "## Problem\ncheck\n\n## Resolution\n"}
    saved = []
    monkeypatch.setattr(claims, "get_claim", lambda _cid: claim)
    monkeypatch.setattr(claims, "update_claim", lambda _cid, fn, **_kw: _mutate_claim(fn, claim, saved))
    monkeypatch.setattr(claims, "_now", lambda: "now")
    monkeypatch.setattr(store, "get_run", lambda _rid: {"env_id": "cr"})
    monkeypatch.setattr(claims_specialist.workspaces, "base", lambda *_args: "/tmp/cr")
    monkeypatch.setattr(claims_specialist.os, "makedirs", lambda *_args, **_kwargs: None)

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
    original = "## Problem\nStep c needs checking\n\n## Evidence\nx\n\n## Research\nNo similar past fix found.\n\n## Resolution\n"
    claim = {"meta": {"run_id": "old-run", "assigned_to": "fixer"}, "body": original}
    monkeypatch.setattr(claims, "get_claim", lambda _cid: claim)
    monkeypatch.setattr(claims, "update_claim", lambda _cid, fn, **_kw: _mutate_claim(fn, claim, []))
    monkeypatch.setattr(claims, "_now", lambda: "now")
    monkeypatch.setattr(store, "get_run", lambda _rid: {"env_id": "cr"})
    monkeypatch.setattr(claims_specialist.workspaces, "base", lambda *_args: "/tmp/cr")
    monkeypatch.setattr(claims_specialist.os, "makedirs", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(claims_specialist, "_prompt", lambda _meta, body: "prompt\n" + body)
    echoed = "The claim was:\n" + original + " [sandbox=workspace-write cwd=cr model=None]"
    monkeypatch.setattr(claims_specialist, "run_specialist", lambda *_args: (0, echoed))

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


def _mutate_claim(fn, claim, writes):
    meta, body = fn(claim["meta"], claim["body"])
    claim.update(meta=meta, body=body)
    writes.append(body)
    return claim
