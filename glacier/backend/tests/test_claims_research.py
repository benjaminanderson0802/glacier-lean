"""Claims are researched and routed automatically the moment they are filed."""
import os, sys, time, textwrap
from conftest import Server

RESEARCHER = textwrap.dedent('''
    import os, sys
    args = sys.argv[1:]
    out = args[args.index("-o") + 1]
    reply = os.environ.get("FAKE_RESEARCH_REPLY", "")
    if reply == "CRASH":
        sys.exit(3)
    open(out, "w").write(reply)
''')


def _server(tmp_path, monkeypatch, reply):
    script = tmp_path / "researcher.py"
    script.write_text(RESEARCHER)
    wrapper = tmp_path / "researcher.sh"
    wrapper.write_text(f"#!/bin/sh\nexec {sys.executable} {script} \"$@\"\n"); wrapper.chmod(0o755)
    monkeypatch.setenv("GLACIER_RESEARCH_BIN", str(wrapper))
    monkeypatch.setenv("FAKE_RESEARCH_REPLY", reply)
    home = tmp_path / "home"; home.mkdir()
    return Server(home).start()


def _wait(s, cid, statuses=("routed", "proposed")):
    deadline = time.time() + 30
    while time.time() < deadline:
        c = s.get(f"/api/claims/{cid}")
        if c["meta"]["status"] in statuses:
            return c
        time.sleep(0.4)
    raise AssertionError(f"claim never routed: {c['meta']}")


def test_environment_claim_goes_to_fixer(tmp_path, monkeypatch):
    s = _server(tmp_path, monkeypatch, "CRASH")  # the researcher is not needed for environment problems
    try:
        cid = s.post("/api/claims", {"kind": "environment", "summary": "Sandbox has no zstd", "evidence": "install failed"})["id"]
        c = _wait(s, cid)
        assert c["meta"]["status"] == "routed" and c["meta"]["assigned_to"] == "fixer"
        assert "No similar past fix found" in c["body"]
    finally:
        s.stop()


def test_gap_with_no_free_option_becomes_a_proposal(tmp_path, monkeypatch):
    s = _server(tmp_path, monkeypatch, "Checked: libfoo (dead), barlib (GPL, no API).\nPaid options: AcmeAPI $20/mo.\nVERDICT: NO FREE OPTION FITS")
    try:
        cid = s.post("/api/claims", {"kind": "capability_gap", "summary": "Need handwriting recognition", "evidence": "nothing local works"})["id"]
        c = _wait(s, cid)
        assert c["meta"]["status"] == "proposed" and c["meta"]["assigned_to"] == "owner"
        assert "## Proposal" in c["body"] and "AcmeAPI" in c["body"]
    finally:
        s.stop()


def test_gap_with_free_option_goes_to_fixer_with_findings(tmp_path, monkeypatch):
    s = _server(tmp_path, monkeypatch, "Option: Tesseract (Apache-2.0, active, 80% fit).\nVERDICT: FREE OPTION FOUND")
    try:
        cid = s.post("/api/claims", {"kind": "capability_gap", "summary": "Need text from scanned images", "evidence": "x"})["id"]
        c = _wait(s, cid)
        assert c["meta"]["status"] == "routed" and c["meta"]["assigned_to"] == "fixer"
        assert "Tesseract" in c["body"] and "## Proposal" not in c["body"]
    finally:
        s.stop()


def test_known_past_fix_is_reused(tmp_path, monkeypatch):
    s = _server(tmp_path, monkeypatch, "CRASH")  # research must not be needed when memory already has the answer
    try:
        old = s.post("/api/claims", {"kind": "capability_gap", "summary": "Need spreadsheet reading for invoices", "evidence": "x"})["id"]
        _wait(s, old)
        s.post(f"/api/claims/{old}/decision", {"action": "approve", "option": "use openpyxl"})
        new = s.post("/api/claims", {"kind": "capability_gap", "summary": "Need spreadsheet reading for receipts", "evidence": "y"})["id"]
        c = _wait(s, new)
        assert f"claims/{old}.md" in c["body"] and "openpyxl" in c["body"]
    finally:
        s.stop()
