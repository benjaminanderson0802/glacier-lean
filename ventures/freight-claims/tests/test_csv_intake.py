from __future__ import annotations

from pathlib import Path
import sys

from ventures.blocks.connectors.common import ConnectorError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from claims import watch_shipments
from csv_intake import parse_shipments_csv


FIXTURES = Path(__file__).parent / "fixtures"


def test_shipments_export_maps_to_api_shipment_shape_and_reports_skipped_rows():
    rows, skipped = parse_shipments_csv(FIXTURES / "shipstation-shipments.csv")

    assert rows == [{
        "shipment_id": "SS-ORD-1042",
        "order_number": "1042",
        "carrier": "Parcel Freight",
        "carrier_code": "parcel_freight",
        "service": "Ground Freight",
        "tracking_number": "TRK-FAKE-1042",
        "ship_date": "2026-10-08",
        "ship_to": {
            "name": "Avery Example",
            "address_line1": "1200 Sample Road",
            "city": "Madison",
            "state": "WI",
            "postal_code": "53703",
            "country": "US",
        },
        "weight_lb": 180.5,
        "shipping_cost": "42.75",
        "order_total": "680.00",
        "items": [{"sku": "PALLET-A", "name": "Ceramic tile", "quantity": 4}],
        "shipment_status": "Exception - damaged pallet",
        "tracking_status": "Exception - damaged pallet",
        "labels": [],
    }]
    assert skipped == [{"row": 3, "reason": "missing tracking number"}]


def test_orders_export_accepts_common_alternate_column_names():
    rows, skipped = parse_shipments_csv(FIXTURES / "shipstation-orders.csv")

    assert skipped == []
    assert rows[0]["shipment_id"] == "SS-ORD-2051"
    assert rows[0]["order_number"] == "2051"
    assert rows[0]["tracking_number"] == "TRK-FAKE-2051"
    assert rows[0]["ship_to"]["address_line1"] == "55 Fictional Ave"
    assert rows[0]["weight_lb"] == 42.0
    assert rows[0]["items"] == [{"sku": "GEAR-9", "name": "Packing gear", "quantity": 2}]


def test_weight_export_in_ounces_is_normalized_to_pounds(tmp_path):
    export = tmp_path / "ounces.csv"
    export.write_text("Tracking Number,Weight (oz)\nTRK-OUNCE,40\n", encoding="utf-8")

    rows, skipped = parse_shipments_csv(export)

    assert skipped == []
    assert rows[0]["weight_lb"] == 2.5


def test_watch_uses_newest_csv_when_api_fails_and_records_skips(tmp_path, monkeypatch):
    home = tmp_path / "ventures" / "freight-claims"
    incoming = home / "incoming"
    incoming.mkdir(parents=True)
    older = incoming / "older.csv"
    newer = incoming / "newer.csv"
    older.write_text("Order Number,Tracking Number,Status\nold,TRK-OLD,delivered\n", encoding="utf-8")
    newer.write_text("Order Number,Tracking Number,Status\nnew,TRK-NEW,damaged\n", encoding="utf-8")
    older.touch()
    newer.touch()
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))

    class UnavailableShipStation:
        def get_shipments(self, **kwargs):
            raise ConnectorError("ShipStation is unavailable")

    result = watch_shipments(client=UnavailableShipStation(), enabled=True)

    assert result["source"] == "csv"
    assert result["csv_file"] == str(newer)
    assert result["candidate_count"] == 1
    assert result["candidates"][0]["shipment_id"] == "new"
    assert result["api_error"] == "ShipStation is unavailable"
    assert result["side_effects"] == []


def test_watch_prefers_working_api_over_available_csv(tmp_path, monkeypatch):
    home = tmp_path / "ventures" / "freight-claims"
    incoming = home / "incoming"
    incoming.mkdir(parents=True)
    (incoming / "shipment.csv").write_text(
        "Order Number,Tracking Number,Status\ncsv,TRK-CSV,damaged\n", encoding="utf-8"
    )
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))

    class WorkingShipStation:
        def get_shipments(self, **kwargs):
            return [{"shipment_id": "api-shipment", "labels": [{"label_id": "label-1"}]}]

        def get_tracking_for_label(self, label_id):
            assert label_id == "label-1"
            return {"status_description": "Delivered"}

    result = watch_shipments(client=WorkingShipStation(), enabled=True)

    assert result["source"] == "api"
    assert result["candidate_count"] == 0


def test_watch_accepts_an_explicit_csv_path_and_reports_skipped_rows(tmp_path, monkeypatch):
    source = tmp_path / "shipments.csv"
    source.write_text(
        "Order Number,Tracking Number,Status\nvalid,TRK-1,exception\nmissing,,shipped\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path / "home"))

    class BrokenIfCalled:
        def get_shipments(self, **kwargs):
            raise AssertionError("explicit CSV intake should be used directly")

    result = watch_shipments(client=BrokenIfCalled(), enabled=False, csv_path=source)

    assert result["source"] == "csv"
    assert result["skipped_rows"] == [{"row": 3, "reason": "missing tracking number"}]
    assert result["candidate_count"] == 1
