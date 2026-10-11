"""Independent CPSC public-source and lawyer-gate acceptance checks."""
import json
import os
import sys
import importlib.util
import json
from urllib.request import Request, urlopen
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "cpsc-prep"))

def load_refresh():
    spec = importlib.util.spec_from_file_location("acceptance_cpsc_refresh", ROOT / "cpsc-prep/scripts/refresh_cpsc_sources.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cpsc_fixture_uses_saferproducts_recall_api_shape():
    payload = json.loads((Path(__file__).parent / "fixtures/cpsc-recall.json").read_text(encoding="utf-8"))
    assert isinstance(payload, list) and payload[0]["RecallID"] == 30123
    assert payload[0]["URL"].startswith("https://www.cpsc.gov/")


@pytest.mark.skipif(os.getenv("CPSC_LIVE") != "1", reason="set CPSC_LIVE=1 for a polite CPSC source canary")
def test_live_saferproducts_recall_endpoint_returns_recall_records():
    request = Request(
        "https://www.saferproducts.gov/RestWebServices/Recall?format=json&RecallID=30123",
        headers={"Accept": "application/json", "User-Agent": "GlacierAcceptanceCanary/1.0 (public data check)"},
    )
    with urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    assert isinstance(payload, list)
    assert all("RecallID" in row or "RecallNumber" in row for row in payload)


def test_lawyer_questions_are_cited_and_launch_remains_gated():
    root = Path(__file__).resolve().parents[2]
    questions = (root / "LAWYER-QUESTIONS.md").read_text(encoding="utf-8").lower()
    manifest = json.loads((root / "venture.json").read_text(encoding="utf-8"))
    assert "https://" in questions and "lawyer" in questions
    assert any("lawyer" in str(gate).lower() or "opinion" in str(gate).lower() for gate in manifest.get("launch_gates", []))
