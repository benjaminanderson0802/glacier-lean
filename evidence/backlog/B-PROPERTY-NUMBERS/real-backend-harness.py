"""Synthetic property-number check invoked as a command node by the real engine."""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ventures" / "property-tax" / "scripts"))
import property_tax


def main() -> int:
    workspace = Path.cwd()
    notice = workspace / "notice.txt"
    notice.write_text("Synthetic notice with a non-finite assessment", encoding="utf-8")
    comp_paths = []
    for index in range(1, 4):
        path = workspace / f"sale-{index}.txt"
        path.write_text("Synthetic comparable", encoding="utf-8")
        comp_paths.append(path)

    source_fields = {
        "notice.txt": {"parcel_id": "1234567890", "assessed_value": "Infinity"},
        "sale-1.txt": {"sale_date": "2026-06-01", "sale_price": "500000", "square_feet": "2000"},
        "sale-2.txt": {"sale_date": "2026-04-01", "sale_price": "480000", "square_feet": "1900"},
        "sale-3.txt": {"sale_date": "2026-02-01", "sale_price": "510000", "square_feet": "2050"},
    }

    def read_document(path, schema=None):
        fields = source_fields[Path(path).name]
        return {
            "fields": {
                key: {"value": value, "page": 1, "confidence": 0.99, "uncertain": False}
                for key, value in fields.items()
            },
            "text": "synthetic fixture",
        }

    property_tax.reader.read_document = read_document
    packet = property_tax.build_packet(
        {
            "parcel_id": "1234567890",
            "notice_path": str(notice),
            "notice_source_url": "https://records.example.test/notices/notice-1",
            "notice_date": "2026-06-15",
            "deadline": "2026-12-15",
            "subject_square_feet": "2,000",
            "customer_requested_value": "$95,000",
            "comparables": [
                {"path": str(path), "source_url": f"https://records.example.test/sale/{index}", "arms_length_confirmed": True}
                for index, path in enumerate(comp_paths, 1)
            ],
        },
        [{"record_id": "1234567890", "data": {"class": "2-11"}, "source_url": "https://data.example.test/roll"}],
        today=date(2026, 6, 15),
    )
    assert packet["result"] == "uncertain — please check"
    assert packet["status"] == "needs_customer_confirmation"
    assert "assessment_notice" not in packet
    assert "comparable_value_estimate" in packet
    assert any("notice-1" in item for item in packet["uncertainties"])
    assert packet["filing_guide"]["notice"]
    print(json.dumps({
        "result": packet["result"],
        "status": packet["status"],
        "uncertainties": packet["uncertainties"],
        "finite_estimate": packet["comparable_value_estimate"],
        "filing_guide_present": bool(packet["filing_guide"]["notice"]),
        "fixture_only": True,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
