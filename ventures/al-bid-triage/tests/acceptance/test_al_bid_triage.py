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


api = load_module(KIT / "scripts/bid_triage.py", "accept_bid")
DOC_URL = "https://alabamabuilds.gov/"
DOC_MARKER = "Alabama Builds"
FIELDS = ("notice_number", "project", "advertising_agency", "county", "municipality", "bid_date", "prebid_meeting", "description", "official_url", "source_mode", "received_at")

@pytest.fixture
def notice():
    # Explicit CUSTOMER mapping of listing fields, not a fabricated official CSV.
    return dict(zip(FIELDS, ["SYN-2026-001", "Public works – José community hall", "Synthetic City",
        "Mobile", "Mobile", "2026-10-21T14:00:00-05:00", "2026-10-15 10:00 CDT",
        "General contractor building construction", "https://alabamabuilds.gov/AdvertisementBids",
        "forwarded_official_notice", "2026-10-10T12:00:00-05:00"]))

def digest(rows):
    return api.build_digest(rows, "general-contracting", {"Mobile", "Baldwin"}, "2026-10-10")

def test_filters_deduplicates_preserves_unicode(notice, tmp_path):
    rows = [notice, dict(notice), dict(notice, notice_number="old", bid_date="2026-10-09"),
            dict(notice, notice_number="elsewhere", county="Pike")]
    path = csv_file(tmp_path / "notices.csv", FIELDS, rows)
    result = digest(api.read_notices(path))
    assert len(result["matches"]) == 1
    assert notice["project"] in api.render_markdown(result)
    assert result["matches"][0]["official_url"] == notice["official_url"]

def test_empty_has_source_and_date_vocabulary():
    text = api.render_markdown(digest([]))
    assert "no notices matched these filters" in text.lower()
    assert "prepared: 2026-10-10" in text.lower() and "source details were supplied" in text.lower()

@pytest.mark.parametrize("field", ["bid_date", "advertising_agency", "prebid_meeting"])
def test_missing_facts_use_uncertain_vocabulary(notice, field):
    notice[field] = ""
    assert uncertain(api.render_markdown(digest([notice])))

def test_conflicting_duplicate_deadlines_not_silently_dropped(notice):
    other = dict(notice, bid_date="2026-10-30")
    try:
        result = digest([notice, other])
    except ValueError:
        return
    assert uncertain(result), "Conflicting versions need human review"

@pytest.mark.parametrize("bad", ["", "wrong,headers\na,b\n", "<html>503 Service unavailable</html>", '{"error":"429 Too Many Requests"}'])
def test_empty_malformed_outage_and_rate_limit_input_produces_no_deliverable(tmp_path, bad):
    path = tmp_path / "input.csv"
    path.write_text(bad, encoding="utf-8")
    with pytest.raises(ValueError):
        api.read_notices(path)

@pytest.mark.parametrize("value", ["not-a-date", "2026-02-30"])
def test_invalid_date_rejected(notice, value):
    notice["bid_date"] = value
    with pytest.raises(ValueError):
        digest([notice])

def test_cli_no_external_actions_or_automatic_payment(notice, tmp_path, monkeypatch):
    path = csv_file(tmp_path / "notices.csv", FIELDS, [notice])
    out = tmp_path / "digest.md"
    assert api.main(["--input", str(path), "--trade", "general-contracting", "--counties", "Mobile", "--as-of", "2026-10-10", "--output", str(out)]) == 0
    assert out.exists()  # socket guard is active; only a local file was written

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
            if "review" in node.get("id", "").lower():
                assert node["type"] == "approval", "Bid digest use requires an owner review step"
                prompt = json.dumps(node, ensure_ascii=False).lower()
                assert "does not send email" in prompt and "file bids" in prompt
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
