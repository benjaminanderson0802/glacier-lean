import claims_research as cr


def _setup(monkeypatch, fixes, verdict, started):
    monkeypatch.setattr(cr, "past_fixes", lambda cid: fixes)
    monkeypatch.setattr(cr, "research", lambda cid: started.append("research") or verdict)
    claim = {"meta": {"kind": "capability_gap", "summary": "need a reader", "run_id": "r1"},
             "body": "## Problem\nx\n\n## Research\n\n## Resolution\n"}
    monkeypatch.setattr(cr.claims, "get_claim", lambda cid: claim)
    def update_claim(_cid, fn, **_kwargs):
        meta, body = fn(claim["meta"], claim["body"])
        claim.update(meta=meta, body=body)
        return claim
    monkeypatch.setattr(cr.claims, "update_claim", update_claim)
    monkeypatch.setattr(cr.claims, "_render", lambda meta, body: "x")
    monkeypatch.setattr(cr.claims, "_path", lambda cid: "claims/x.md")
    monkeypatch.setattr(cr.store.broadcaster, "publish", lambda e: None)
    import claims_specialist
    monkeypatch.setattr(claims_specialist, "maybe_start", lambda cid, role: started.append(role))


def test_capability_gap_is_researched_even_with_past_fixes(monkeypatch):
    started = []
    _setup(monkeypatch, ["claims/old.md: reader -> fixed"], "VERDICT: FREE OPTION FOUND", started)
    r = cr.research_claim.__wrapped__("c1")
    assert "research" in started and r["assigned_to"] == "fixer" and "fixer" in started


def test_similar_past_claim_does_not_override_a_no_free_option_verdict(monkeypatch):
    started = []
    _setup(monkeypatch, ["claims/old.md: reader -> fixed"], "VERDICT: NO FREE OPTION FITS", started)
    r = cr.research_claim.__wrapped__("c2")
    assert r["assigned_to"] == "owner" and r["status"] == "proposed" and "fixer" not in started


def test_no_fix_and_no_free_option_goes_to_owner(monkeypatch):
    started = []
    _setup(monkeypatch, [], "VERDICT: NO FREE OPTION FITS", started)
    r = cr.research_claim.__wrapped__("c3")
    assert r["assigned_to"] == "owner" and r["status"] == "proposed" and "fixer" not in started
