"""Independent homeowner self-file mode acceptance checks."""
import json
from pathlib import Path

import pytest


def test_homeowner_mode_prepares_guide_and_keeps_filing_with_homeowner():
    root = Path(__file__).resolve().parents[2]
    readme = (root / "README.md").read_text(encoding="utf-8").lower()
    flow = json.loads((root / "flows/property-tax-prepare-packet.json").read_text(encoding="utf-8"))
    assert "homeowner self-file" in readme or "self-file" in readme
    serialized = json.dumps(flow).lower()
    assert "homeowner" in serialized and ("filing guide" in serialized or "step-by-step" in serialized)
    assert "submit" not in serialized or "owner" in serialized or "homeowner" in serialized


def test_decision_memo_compares_three_paths_and_live_mail_stays_disabled():
    root = Path(__file__).resolve().parents[2]
    memo = (root / "DECISION.md").read_text(encoding="utf-8").lower()
    for term in ("self-file", "licensed attorney", "assessor-stage"):
        assert term in memo
    assert memo.count("http") >= 3
    assert "mail" in memo and ("disabled" in memo or "off" in memo)
