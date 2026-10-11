"""Independent T-PILOTS checks. Field provenance: ACCEPTANCE.md.
Synthetic fixtures are defined here, independently of builder fixtures.
"""
import csv
import importlib.util
import io
import json
import os
import socket
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest

KIT = Path(__file__).resolve().parents[2]
ROOT = KIT.parents[1]
sys.path.insert(0, str(ROOT))

def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class ExternalNetworkBlocked(RuntimeError):
    """Raised before an offline check can open a non-loopback connection."""


_ORIGINAL_SOCKET_CONNECT = socket.socket.connect
_ORIGINAL_SOCKET_CONNECT_EX = socket.socket.connect_ex


def _is_event_loop_socketpair(sock, address):
    if not isinstance(address, tuple) or not address:
        return False
    try:
        import ipaddress
        if not ipaddress.ip_address(address[0]).is_loopback:
            return False
    except ValueError:
        return False

    frame = sys._getframe(1)
    found_socketpair = False
    found_asyncio = False
    while frame is not None:
        filename = frame.f_code.co_filename.replace("\\", "/")
        found_socketpair |= frame.f_code.co_name == "socketpair" and filename.endswith("/socket.py")
        found_asyncio |= "/asyncio/" in filename
        frame = frame.f_back
    return found_socketpair and found_asyncio


def _blocked_connect(sock, address):
    if _is_event_loop_socketpair(sock, address):
        return _ORIGINAL_SOCKET_CONNECT(sock, address)
    raise ExternalNetworkBlocked(f"Offline acceptance blocked connection to {address!r}")


def _blocked_connect_ex(sock, address):
    if _is_event_loop_socketpair(sock, address):
        return _ORIGINAL_SOCKET_CONNECT_EX(sock, address)
    raise ExternalNetworkBlocked(f"Offline acceptance blocked connection to {address!r}")


@pytest.fixture(autouse=True)
def no_accidental_network(monkeypatch, request):
    if "live" not in request.node.name:
        monkeypatch.setattr(socket.socket, "connect", _blocked_connect)
        monkeypatch.setattr(socket.socket, "connect_ex", _blocked_connect_ex)


@pytest.mark.parametrize("address", [("127.0.0.1", 9), ("192.0.2.1", 443)])
def test_connections_outside_event_loop_socketpair_are_refused(address):
    with socket.socket() as sock:
        with pytest.raises(ExternalNetworkBlocked):
            sock.connect(address)


def uncertain(value):
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    return "uncertain - please check" in text.replace("—", "-").replace("–", "-").lower()


def csv_file(path, fields, rows, delimiter=","):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)
    return path


api = load_module(KIT / "scripts/fee_digest.py", "accept_fba")
DOC_URL = "https://developer-docs.amazon.com/sp-api/docs/report-type-values-settlement"
DOC_MARKER = "quantity-purchased"
# Every column is from Amazon's Flat File V2 attribute list; values synthetic.
FIELDS = "settlement-id settlement-start-date settlement-end-date deposit-date total-amount currency transaction-type order-id merchant-order-id adjustment-id shipment-id marketplace-name amount-type amount-description amount fulfillment-id posted-date posted-date-time order-item-code merchant-order-item-id merchant-adjustment-item-id sku quantity-purchased promotion-id".split()
SCHEDULE = ["sku", "size_tier", "expected_fee_usd_per_unit", "unit_cost_usd"]

def row(**changes):
    result = {key: "" for key in FIELDS}
    result.update({"settlement-id": "100001", "currency": "USD", "transaction-type": "Order",
        "order-id": "111-1234567-1234567", "shipment-id": "ship-1", "order-item-code": "item-1",
        "fulfillment-id": "AFN", "sku": "TAZA-É-茶", "quantity-purchased": "2",
        "amount-type": "ItemFees", "amount-description": "FBAPerUnitFulfillmentFee", "amount": "-10.50"})
    result.update(changes)
    return result

@pytest.fixture
def files(tmp_path):
    def make(rows=None, expectations=True):
        report = csv_file(tmp_path / "settlement.tsv", FIELDS, rows if rows is not None else [
            row(**{"amount-type": "ItemPrice", "amount-description": "Principal", "amount": "40.00"}), row()], "\t")
        schedule = csv_file(tmp_path / "expected.csv", SCHEDULE, [{"sku": "TAZA-É-茶", "size_tier": "Large standard",
            "expected_fee_usd_per_unit": "5.00", "unit_cost_usd": "7.00"}] if expectations else [])
        return report, schedule
    return make

def test_multiunit_variance_margin_and_source_references(files):
    result, = api.analyze_reports(*files())
    assert result["sku"] == "TAZA-É-茶"
    assert result["source_report_row"] == "3"
    assert result["source_shipment_id"] == "ship-1"
    assert result["source_order_item_code"] == "item-1"
    assert result["variance_usd"] == "0.50"
    assert result["expected_unit_margin_usd"] == "8.00"
    assert result["observed_unit_margin_usd"] == "7.75"
    assert "not a fee refund guarantee" in result["disclaimer"]

def test_split_shipments_do_not_double_count_sale_margin(files):
    sale = row(**{"amount-type": "ItemPrice", "amount-description": "Principal", "amount": "40.00"})
    second_sale = dict(sale, **{"shipment-id": "ship-2", "order-item-code": "item-2", "amount": "60.00", "quantity-purchased": "3"})
    second_fee = row(**{"shipment-id": "ship-2", "order-item-code": "item-2", "amount": "-15.00", "quantity-purchased": "3"})
    results = api.analyze_reports(*files([sale, row(), second_sale, second_fee]))
    assert [r["expected_unit_margin_usd"] for r in results] == ["8.00", "8.00"]

def test_settlement_summary_row_does_not_create_fee_and_detail_currency_is_used(files):
    summary = {key: "" for key in FIELDS}
    summary.update({"settlement-id": "100001", "settlement-start-date": "2026-10-01", "settlement-end-date": "2026-10-09", "deposit-date": "2026-10-10", "total-amount": "29.50", "currency": "USD"})
    result = api.analyze_reports(*files([summary, row(currency="USD")]))
    assert len(result) == 1 and result[0]["actual_fee_usd"] == "10.50"

def test_empty_valid_report_has_no_fees(files):
    assert api.analyze_reports(*files([])) == []

@pytest.mark.parametrize("case", ["missing_expectation", "missing_quantity", "negative_quantity"])
def test_partial_data_uses_uncertain_vocabulary(files, case):
    fee = row()
    if case == "missing_quantity": fee["quantity-purchased"] = ""
    if case == "negative_quantity": fee["quantity-purchased"] = "-2"
    result = api.analyze_reports(*files([fee], expectations=case != "missing_expectation"))
    assert uncertain(result)

@pytest.mark.parametrize("amount", ["NaN", "Infinity", "not-money", "10,50"])
def test_nonfinite_or_malformed_amount_rejected(files, amount):
    with pytest.raises(ValueError):
        api.analyze_reports(*files([row(amount=amount)]))

def test_wrong_currency_rejected(files):
    with pytest.raises(ValueError):
        api.analyze_reports(*files([row(currency="EUR")]))

@pytest.mark.parametrize("body", ["", "wrong\nheader\n", "<html>503 Service Unavailable</html>", '{"error":"429 Too Many Requests"}'])
def test_bad_source_has_no_deliverable_or_charge(files, tmp_path, body):
    report, schedule = files()
    report.write_text(body, encoding="utf-8")
    out = tmp_path / "digest.csv"
    with pytest.raises(ValueError):
        api.write_digest(report, schedule, out)
    assert not out.exists()

def test_local_digest_never_contacts_amazon_or_payment_service(files, tmp_path):
    report, schedule = files()
    output = tmp_path / "digest.csv"
    api.write_digest(report, schedule, output)
    assert "TAZA-É-茶" in output.read_text(encoding="utf-8")  # real network is blocked by autouse guard

@pytest.mark.skipif(os.environ.get("RUN_LIVE") != "1", reason="Set RUN_LIVE=1 for public read-only canaries")
def test_live_official_document_contract():
    # No customer information, credentials, account requests or external writes.
    request = Request(DOC_URL, headers={"User-Agent": "Glacier-independent-acceptance/1.0"})
    with urlopen(request, timeout=25) as response:
        body = response.read(4_000_000).decode("utf-8", errors="replace")
        assert response.status == 200
        assert DOC_MARKER.lower() in body.lower(), "Official document changed or challenge page returned"
        print(f"LIVE document: {response.status} {response.url}; marker={DOC_MARKER}")


def test_owner_only_flow_boundaries():
    for path in (KIT / "flows").glob("*.json"):
        flow = json.loads(path.read_text(encoding="utf-8"))
        nodes = flow.get("nodes", flow.get("steps", []))
        assert nodes
        assert {n["type"] for n in nodes} <= {"approval", "check", "note", "command", "connector"}
        for node in nodes:
            if node["type"] == "connector":
                assert node.get("read_only") is True
            if "pitch" in node.get("id", "").lower():
                assert node["type"] == "approval", "Prospect contact must stay owner-only"
                prompt = json.dumps(node, ensure_ascii=False).lower()
                assert "manually send the pitch" in prompt and "glacier does not send anything" in prompt
            if node["type"] == "command":
                command = node.get("command", node.get("config", {}).get("cmd", ""))
                assert KIT.relative_to(ROOT).as_posix() + "/scripts/" in command
                assert not any(token in command.lower() for token in ("curl ", "sendmail", "stripe", "apify push", "git push"))


def test_prospect_rows_have_business_provenance():
    from urllib.parse import urlparse
    rows = list(csv.DictReader((KIT / "prospects.csv").open(encoding="utf-8", newline="")))
    assert rows
    for row in rows:
        source = row.get("official_source_url") or row.get("source_url") or row.get("official_public_directory_source_url")
        assert source and urlparse(source).scheme == "https"
        email = row.get("business_email", "")
        assert not email or email.split("@")[-1] not in {"gmail.com", "yahoo.com", "hotmail.com"}
        assert row.get("business_phone") or row.get("public_business_contact_url") or email
