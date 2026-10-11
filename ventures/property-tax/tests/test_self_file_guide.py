from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ventures" / "property-tax" / "scripts"))

import property_tax


def test_packet_includes_homeowner_self_file_guide_and_keeps_filing_manual(tmp_path):
    packet = {
        "county": "Cook County",
        "parcel_id": "12345678901234",
        "result": "match",
        "as_of": "2026-10-10",
        "filing_submitted": False,
        "legal_review_notice": "The homeowner reviews, signs, and files.",
        "parcel": {"parcel_id": "12345678901234", "township": "Example"},
        "comparables": [],
        "customer_requested_value": 95000,
        "uncertainties": [],
    }

    output = property_tax.render_packet(packet, tmp_path / "case.json")
    rendered = json.loads(output.read_text(encoding="utf-8"))
    markdown = output.with_suffix(".md").read_text(encoding="utf-8")

    assert rendered["filing_mode"] == "homeowner_self_file"
    assert rendered["filing_submitted"] is False
    assert rendered["filing_guide_path"] == str(output.with_name("case-filing-guide.md"))
    assert "individual taxpayer" in rendered["filing_guide"]["eligibility"].lower()
    assert "https://www.cookcountyassessoril.gov/online-appeals" in markdown
    assert "https://www.cookcountyboardofreview.com/assessment-appeals/residential" in markdown
    assert "assessment-calendar-and-deadlines" in markdown
    assert "sign and submit your own appeal" in markdown.lower()
    assert "glacier did not file anything" in markdown.lower()
