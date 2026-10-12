"""Independent Indiana utility audit and unsigned ST-200 data checks."""
import json
import sys
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "utility-audits"))

def load_utility_audit():
    spec = importlib.util.spec_from_file_location("acceptance_utility_audit", ROOT / "utility-audits/scripts/utility_audit.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_existing_calculator_keeps_output_an_estimate_and_unsigned():
    calculate_audit = load_utility_audit().calculate_audit
    fixture = json.loads((Path(__file__).resolve().parents[2] / "tests/sample_audit.json").read_text(encoding="utf-8"))
    result = calculate_audit(fixture)
    assert result.get("result") in {"match", "uncertain"}
    assert result.get("submitted", False) is False


def test_bulletin_55_and_decision_memo_are_source_backed():
    root = Path(__file__).resolve().parents[2]
    memo = (root / "DECISION.md").read_text(encoding="utf-8").lower()
    readme = (root / "README.md").read_text(encoding="utf-8").lower()
    assert "bulletin #55" in readme or "bulletin 55" in readme
    for term in ("indiana", "alternative", "source"):
        assert term in memo
    assert memo.count("https://") >= 3


def test_utility_bills_csv_builds_unsigned_st200_application_data(tmp_path):
    utility_audit = load_utility_audit()
    build = getattr(utility_audit, "prepare_st200", None) or getattr(utility_audit, "prepare_application", None)
    assert callable(build)
    result = build(tmp_path / "bills.csv", output_dir=tmp_path)
    assert result.get("signed") is False and result.get("submitted") is False
