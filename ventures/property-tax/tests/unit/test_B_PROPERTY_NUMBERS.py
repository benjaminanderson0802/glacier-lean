from __future__ import annotations

import math
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "ventures" / "property-tax" / "scripts"))

import property_tax


ROLL_ROWS = [
    {
        "record_id": "1234567890",
        "data": {"class": "2-11", "township_name": "Example"},
        "source_url": "https://data.example.test/roll/1234567890",
    }
]


def _reader_field(value, page=1):
    return {"value": value, "page": page, "confidence": 0.99, "uncertain": False}


def _packet(monkeypatch, tmp_path, *, assessed="100000", prices=None, areas=None, subject="2000", requested="95000"):
    prices = prices or ["500000", "480000", "510000"]
    areas = areas or ["2000", "1900", "2050"]
    notice = tmp_path / "notice.txt"
    notice.write_text("synthetic notice", encoding="utf-8")
    comps = []
    reader_fields = {
        "notice.txt": {
            "parcel_id": "1234567890",
            "assessed_value": assessed,
        }
    }
    for index, (price, area) in enumerate(zip(prices, areas), 1):
        path = tmp_path / f"sale-{index}.txt"
        path.write_text("synthetic sale", encoding="utf-8")
        comps.append(
            {
                "path": str(path),
                "source_url": f"https://records.example.test/sale/{index}",
                "arms_length_confirmed": True,
            }
        )
        reader_fields[path.name] = {
            "sale_date": "2026-06-01" if index == 1 else ("2026-04-01" if index == 2 else "2026-02-01"),
            "sale_price": price,
            "square_feet": area,
        }

    def read_document(path, schema=None):
        return {
            "fields": {key: _reader_field(value) for key, value in reader_fields[Path(path).name].items()},
            "text": "synthetic source text",
        }

    monkeypatch.setattr(property_tax.reader, "read_document", read_document)
    case = {
        "parcel_id": "1234567890",
        "notice_path": str(notice),
        "notice_source_url": "https://records.example.test/notices/notice-1",
        "notice_date": "2026-06-15",
        "deadline": "2026-12-15",
        "subject_square_feet": subject,
        "subject_square_feet_source_url": "https://records.example.test/property/area-1",
        "customer_requested_value": requested,
        "comparables": comps,
    }
    return property_tax.build_packet(case, ROLL_ROWS, today=date(2026, 6, 15))


@pytest.mark.parametrize("value", ["Infinity", "-Infinity", "NaN", "1e309", "1e999999", "not a number", "1,2"])
def test_B_PROPERTY_NUMBERS_rejects_invalid_monetary_values(value):
    assert property_tax._number(value, kind="money") is None


@pytest.mark.parametrize("value", [0, "0", -1, "-1"])
def test_B_PROPERTY_NUMBERS_rejects_nonpositive_amounts(value):
    assert property_tax._number(value, kind="money") is None


def test_B_PROPERTY_NUMBERS_parses_valid_formatted_monetary_and_area_values():
    assert property_tax._number("$1,234,567.89", kind="money") == 1234567.89
    assert property_tax._number("1,234.5", kind="area") == 1234.5
    assert property_tax._number(True, kind="money") is None


@pytest.mark.parametrize("value", ["Infinity", "NaN", "1e309", "0", "-25", "1,2"])
def test_B_PROPERTY_NUMBERS_notice_amount_rejection_keeps_source_uncertainty(monkeypatch, tmp_path, value):
    packet = _packet(monkeypatch, tmp_path, assessed=value)

    assert packet["result"] == "uncertain — please check"
    assert packet["status"] == "needs_customer_confirmation"
    assert any("notice-1" in item for item in packet["uncertainties"])
    assert "assessment_notice" not in packet
    assert math.isfinite(packet["comparable_value_estimate"])
    assert packet["filing_guide"]["notice"]


@pytest.mark.parametrize("value", ["Infinity", "NaN", "1e309", "0", "-200", "1,2"])
def test_B_PROPERTY_NUMBERS_comparable_amount_rejection_keeps_source_uncertainty(monkeypatch, tmp_path, value):
    packet = _packet(monkeypatch, tmp_path, prices=[value, "480000", "510000"])

    assert packet["result"] == "uncertain — please check"
    assert packet["status"] == "needs_customer_confirmation"
    assert any("sale/1" in item for item in packet["uncertainties"])
    assert len(packet["comparables"]) == 2
    assert "comparable_value_estimate" not in packet


@pytest.mark.parametrize("value", ["Infinity", "NaN", "1e309", "0", "-200", "1,2", "$2,000"])
def test_B_PROPERTY_NUMBERS_area_rejection_keeps_source_uncertainty(monkeypatch, tmp_path, value):
    packet = _packet(monkeypatch, tmp_path, areas=["2000", value, "2050"], subject=value)

    assert packet["result"] == "uncertain — please check"
    assert any("sale/2" in item for item in packet["uncertainties"])
    assert any("area-1" in item for item in packet["uncertainties"])
    assert "comparable_value_estimate" not in packet


@pytest.mark.parametrize("value", ["Infinity", "NaN", "1e309", "0", "-95000", "1,2"])
def test_B_PROPERTY_NUMBERS_requested_value_rejection_does_not_emit_raw_invalid_value(monkeypatch, tmp_path, value):
    packet = _packet(monkeypatch, tmp_path, requested=value)

    assert packet["customer_requested_value"] is None
    assert any("customer_requested_value" in item for item in packet["uncertainties"])
    assert packet["result"] == "uncertain — please check"
    assert packet["filing_guide"]["notice"]


def test_B_PROPERTY_NUMBERS_derived_overflow_is_uncertain_without_estimate(monkeypatch, tmp_path):
    packet = _packet(monkeypatch, tmp_path, prices=["1e308", "1e308", "1e308"], areas=["1", "1", "1"], subject="1e308")

    assert packet["result"] == "uncertain — please check"
    assert "comparable_value_estimate" not in packet
    assert any("sale/1" in item for item in packet["uncertainties"])
    assert any("area-1" in item for item in packet["uncertainties"])


def test_B_PROPERTY_NUMBERS_valid_formatted_packet_has_finite_arithmetic(monkeypatch, tmp_path):
    packet = _packet(
        monkeypatch,
        tmp_path,
        assessed="$100,000.00",
        prices=["$500,000", "$480,000", "$510,000"],
        areas=["2,000", "1,900", "2,050"],
        subject="2,000",
        requested="$95,000",
    )

    assert packet["result"] == "match"
    assert packet["assessment_notice"]["assessed_value"] == 100000
    assert packet["customer_requested_value"] == 95000
    assert packet["comparable_value_estimate"] == 500000
    assert math.isfinite(packet["comparable_value_estimate"])
    assert packet["filing_guide"]["notice"]
