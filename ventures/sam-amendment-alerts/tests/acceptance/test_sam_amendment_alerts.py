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

@pytest.fixture(autouse=True)
def no_accidental_network(monkeypatch, request):
    if "live" not in request.node.name:
        def blocked(*args, **kwargs):
            pytest.fail("Offline acceptance attempted a real network connection")
        monkeypatch.setattr(socket.socket, "connect", blocked)


def uncertain(value):
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    return "uncertain - please check" in text.replace("—", "-").replace("–", "-").lower()


def csv_file(path, fields, rows, delimiter=","):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)
    return path


api = load_module(KIT / "scripts/digest.py", "accept_sam")
DOC_URL = "https://open.gsa.gov/api/get-opportunities-public-api/"
DOC_MARKER = "opportunitiesData"

@pytest.fixture
def notice():
    # GSA's v2 example uses responseDeadLine (table has a spelling inconsistency).
    return {"noticeId": "1" * 32, "title": "Válvulas – industrial supplies",
            "solicitationNumber": "TEST-26-001", "naicsCode": "423840",
            "responseDeadLine": "2026-10-20T14:00:00-05:00",
            "uiLink": "https://sam.gov/opp/" + "1" * 32 + "/view",
            "links": [{"rel": "self", "href": "https://api.sam.gov/opportunities/v2/search?noticeid=" + "1" * 32}]}

def snapshot(rows):
    # retrieved_at/source_url are local capture metadata, not GSA response fields.
    return {"totalRecords": len(rows), "limit": 100, "offset": 0, "opportunitiesData": rows,
            "retrieved_at": "2026-10-10T14:00:00Z", "source_url": "https://api.sam.gov/opportunities/v2/search"}

def digest(before, after):
    return api.build_digest(before, after, naics_codes={"423840"})

def test_new_and_deadline_change_unicode(notice):
    result = digest(snapshot([]), snapshot([notice]))
    assert result["events"][0]["title"] == notice["title"]
    updated = dict(notice, responseDeadLine="2026-10-22T14:00:00-05:00")
    changed = digest(snapshot([notice]), snapshot([updated]))
    assert changed["events"][0]["kind"] == "deadline_change"
    assert changed["events"][0]["previous_deadline"] == notice["responseDeadLine"]

def test_empty_complete_snapshot_is_dated_no_match():
    assert digest(snapshot([]), snapshot([]))["status"] == "no match found in SAM.gov as of 2026-10-10"

def test_missing_notice_is_not_cancellation(notice):
    assert not digest(snapshot([notice]), snapshot([]))["events"]

def test_notice_link_does_not_require_customer_api_key(notice):
    event = digest(snapshot([]), snapshot([notice]))["events"][0]
    assert event["source_url"] == notice["uiLink"], "API self link requires a key; preserve supplied notice UI link"

@pytest.mark.parametrize("case", ["partial_page", "missing_retrieval", "malformed_row", "missing_deadline", "duplicate_conflict"])
def test_partial_data_rejected_or_uncertain(notice, case):
    after = snapshot([notice])
    if case == "partial_page":
        after["totalRecords"] = 101
    elif case == "missing_retrieval":
        after.pop("retrieved_at")
    elif case == "malformed_row":
        after["opportunitiesData"] = [None]
    elif case == "missing_deadline":
        notice.pop("responseDeadLine")
    else:
        after["opportunitiesData"].append(dict(notice, responseDeadLine="2026-11-01T10:00:00Z"))
        after["totalRecords"] = 2
    try:
        result = digest(snapshot([]), after)
    except ValueError:
        return
    if case == "missing_deadline":
        assert result["events"] and uncertain(result["events"][0].get("response_deadline", "")), "Missing deadline needs explicit uncertainty"
    else:
        assert uncertain(result), "Incomplete source cannot support a confident match/no-match"

@pytest.mark.parametrize("body", [{}, {"opportunitiesData": None}, {"error": {"code": "API_UNAVAILABLE", "message": "Service unavailable"}}, {"error": {"code": "OVER_RATE_LIMIT", "message": "Rate limit exceeded"}}])
def test_outage_rate_limit_malformed_fail_closed(body):
    # Error envelope is an injected failure, not a successful GSA response schema.
    with pytest.raises(ValueError):
        digest(snapshot([]), body)

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
        flow = json.loads(path.read_text())
        nodes = flow.get("nodes", flow.get("steps", []))
        assert nodes
        assert {n["type"] for n in nodes} <= {"approval", "check", "note", "command", "connector"}
        for node in nodes:
            if node["type"] == "connector":
                assert node.get("read_only") is True
            if node["type"] == "command":
                command = node.get("command", node.get("config", {}).get("cmd", ""))
                assert "digest.py" in command and "--before" in command and "--after" in command
            assert node["type"] not in {"email", "http_request", "payment", "publish", "bid_submit"}
            if node["type"] == "command":
                command = node.get("command", node.get("config", {}).get("cmd", ""))
                assert str(KIT.relative_to(ROOT)) + "/scripts/" in command
                assert not any(token in command.lower() for token in ("curl ", "sendmail", "stripe", "apify push", "git push"))


def test_prospect_rows_have_business_provenance():
    from urllib.parse import urlparse
    rows = list(csv.DictReader((KIT / "prospects.csv").open()))
    assert rows
    for row in rows:
        source = row.get("official_source_url") or row.get("source_url") or row.get("official_public_directory_source_url")
        assert source and urlparse(source).scheme == "https"
        email = row.get("business_email", "")
        assert not email or email.split("@")[-1] not in {"gmail.com", "yahoo.com", "hotmail.com"}
        assert row.get("business_phone") or row.get("public_business_contact_url") or email
