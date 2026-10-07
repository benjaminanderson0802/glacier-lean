import claims_research as cr


def _setup(monkeypatch, fixes, verdict, started):
    monkeypatch.setattr(cr, "past_fixes", lambda cid: fixes)
    monkeypatch.setattr(cr, "research", lambda cid: started.append("research") or verdict)
    monkeypatch.setattr(cr.claims, "get_claim", lambda cid: {"meta": {"kind": "capability_gap", "summary": "need a reader", "run_id": "r1"},
                                                            "body": "## Problem\nx\n\n## Research\n\n## Resolution\n"})
    monkeypatch.setattr(cr.claims, "_render", lambda meta, body: "x")
    monkeypatch.setattr(cr.claims, "_path", lambda cid: "claims/x.md")
    monkeypatch.setattr(cr.vault, "write_note", lambda *a, **k: None)
    monkeypatch.setattr(cr.store.broadcaster, "publish", lambda e: None)
    import claims_specialist
    monkeypatch.setattr(claims_specialist, "maybe_start", lambda cid, role: started.append(role))


def test_capability_gap_is_researched_even_with_past_fixes(monkeypatch):
    started = []
    _setup(monkeypatch, ["claims/old.md: reader -> fixed"], "VERDICT: FREE OPTION FOUND", started)
    r = cr.research_claim.__wrapped__("c1")
    assert "research" in started and r["assigned_to"] == "fixer" and "fixer" in started


def test_past_resolved_fix_counts_as_free_option(monkeypatch):
    started = []
    _setup(monkeypatch, ["claims/old.md: reader -> fixed"], "VERDICT: NO FREE OPTION FITS", started)
    assert cr.research_claim.__wrapped__("c2")["assigned_to"] == "fixer"


def test_no_fix_and_no_free_option_goes_to_owner(monkeypatch):
    started = []
    _setup(monkeypatch, [], "VERDICT: NO FREE OPTION FITS", started)
    r = cr.research_claim.__wrapped__("c3")
    assert r["assigned_to"] == "owner" and r["status"] == "proposed" and "fixer" not in started
