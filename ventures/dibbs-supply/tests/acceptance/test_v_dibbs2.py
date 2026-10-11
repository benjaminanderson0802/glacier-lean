"""Independent SAM.gov opportunity and owner bid-gate acceptance checks."""
import json
import sys
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "dibbs-supply"))

def load_dibbs():
    spec = importlib.util.spec_from_file_location("acceptance_dibbs_supply", ROOT / "dibbs-supply/scripts/dibbs_supply.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sam_v2_fixture_has_real_search_response_shape():
    payload = json.loads((Path(__file__).parent / "fixtures/sam-opportunities-v2.json").read_text())
    assert payload["totalRecords"] == len(payload["opportunitiesData"])
    record = payload["opportunitiesData"][0]
    assert {"noticeId", "solicitationNumber", "title", "department", "naicsCode", "responseDeadLine", "uiLink"} <= set(record)


@pytest.mark.xfail(strict=False, reason="awaiting builder V-DIBBS2")
def test_sam_opportunity_filter_ranks_dla_and_owner_naics_without_consent_clickthrough():
    dibbs_supply = load_dibbs()
    fixture = json.loads((Path(__file__).parent / "fixtures/sam-opportunities-v2.json").read_text())
    normalize = getattr(dibbs_supply, "parse_sam_opportunities", None) or getattr(dibbs_supply, "normalize_sam_response", None)
    assert normalize is not None
    rows = normalize(fixture, naics_codes={"423840", "423830", "423710", "423610", "423120"})
    assert rows and rows[0]["source_url"].startswith("https://sam.gov/")
    assert rows[0]["naics_code"] == "423840"


def test_quote_workflow_preserves_manual_signature_and_submit_gate():
    root = Path(__file__).resolve().parents[2]
    readme = (root / "README.md").read_text().lower()
    manifest = json.loads((root / "venture.json").read_text())
    assert "sign and submit" in readme or "sign" in readme and "submit" in readme
    assert any("bid" in str(step).lower() and ("owner" in str(step).lower() or "your step" in str(step).lower())
               for step in manifest.get("your_steps", []))


@pytest.mark.xfail(strict=False, reason="awaiting builder V-DIBBS2")
def test_sam_api_key_is_a_named_secret_and_never_checked_into_fixture():
    root = Path(__file__).resolve().parents[2]
    manifest = json.loads((root / "venture.json").read_text())
    assert any("sam_api_key" in str(value).lower() for value in manifest.get("secrets_needed", []))
    fixture = (Path(__file__).parent / "fixtures/sam-opportunities-v2.json").read_text()
    assert "api_key" not in fixture.lower() and "apiKey" not in fixture
