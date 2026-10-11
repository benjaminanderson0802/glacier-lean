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


api = load_module(KIT / "scripts/generate_packet.py", "accept_job")
DOC_URL = "https://developer.getjobber.com/docs/"
DOC_MARKER = "completedAt"

@pytest.fixture
def job():
    # Official Job/Client fields; nullable property is valid. No invented API fields.
    return {"id": "Z2lkOi8vSm9iYmVyL0pvYi85MDAx", "jobNumber": 9001,
            "title": "Heat pump installation", "jobStatus": "COMPLETED",
            "completedAt": "2026-10-09T15:30:00-05:00", "customFields": [],
            "client": {"name": "José 李"}, "property": None}

def envelope(jobs):
    return {"data": {"account": {"name": "Synthetic HVAC"},
                     "jobs": {"nodes": jobs, "pageInfo": {"hasNextPage": False, "endCursor": None}}},
            "extensions": {"versioning": {"version": "2026-04-16"}}}

def test_completed_packet_and_markdown_preserve_source(job, tmp_path):
    packet = api.build_packet(job, "Synthetic HVAC")
    md, pdf = api.write_packet(packet, tmp_path)
    assert "José 李" in md.read_text(encoding="utf-8")
    assert packet["completion_date"] == "2026-10-09"
    assert pdf.read_bytes().startswith(b"%PDF-")
    assert "not a code, safety, or workmanship certification" in md.read_text(encoding="utf-8")
    assert uncertain(packet["invoice_reference"])

@pytest.mark.parametrize("status", ["UPCOMING", "", None])
def test_incomplete_jobs_rejected(job, status):
    job["jobStatus"] = status
    with pytest.raises(ValueError):
        api.build_packet(job, "Synthetic HVAC")

def test_pdf_preserves_unicode_customer_name(job):
    pdf = api.render_pdf(api.render_markdown(api.build_packet(job, "Synthetic HVAC")))
    assert "José 李".encode("utf-8") in pdf

def test_missing_completion_is_uncertain(job):
    job["completedAt"] = None
    assert uncertain(api.build_packet(job, "Synthetic HVAC")["completion_date"])

def test_malformed_completion_not_asserted_as_fact(job):
    job["completedAt"] = "not-a-date"
    try:
        packet = api.build_packet(job, "Synthetic HVAC")
    except ValueError:
        return
    assert uncertain(packet["completion_date"])

@pytest.mark.parametrize("case", ["partial_page", "partial_graphql", "outage", "rate_limit"])
def test_partial_or_failed_source_never_delivers_packet(job, tmp_path, case, capsys):
    payload = envelope([job])
    if case == "partial_page":
        payload["data"]["jobs"]["pageInfo"] = {"hasNextPage": True, "endCursor": "cursor-1"}
    else:
        payload["errors"] = [{"message": {"partial_graphql": "Field resolution failed", "outage": "Service unavailable", "rate_limit": "Throttled"}[case]}]
        if case != "partial_graphql":
            payload["data"] = None
    source = tmp_path / "job.json"
    source.write_text(json.dumps(payload), encoding="utf-8")
    out = tmp_path / "packets"
    try:
        rc = api.main(["--fixture", str(source), "--output-dir", str(out)])
    except Exception as exc:
        assert not list(out.glob("*.pdf")) if out.exists() else True
        pytest.fail(f"source uncertainty escaped as an unhandled exception: {exc!r}")
    assert rc != 0, "Incomplete/error GraphQL response was accepted as deliverable"
    assert not list(out.glob("*.pdf")), "No source-outage-only deliverable may be billed"
    assert uncertain(capsys.readouterr().err)

def test_empty_source_no_packets(tmp_path, capsys):
    source = tmp_path / "empty.json"
    source.write_text(json.dumps(envelope([])), encoding="utf-8")
    assert api.main(["--fixture", str(source), "--output-dir", str(tmp_path / "out")]) == 0
    assert json.loads(capsys.readouterr().out)["packets_created"] == 0

@pytest.mark.parametrize("status", [429, 503])
def test_real_connector_outage_has_no_packet_or_payment(monkeypatch, tmp_path, capsys, status):
    import httpx
    from ventures.blocks.connectors import JobberClient
    def unavailable(request):
        assert "mutation" not in request.content.decode().lower()
        return httpx.Response(status, json={"errors": [{"message": "source unavailable"}]})
    client = JobberClient(access_token="synthetic-token", transport=httpx.MockTransport(unavailable), sleep=lambda _: None)
    monkeypatch.setattr(api, "JobberClient", lambda: client)
    assert api.main(["--jobber", "--output-dir", str(tmp_path)]) != 0
    assert not list(tmp_path.glob("*.pdf"))
    assert json.loads(capsys.readouterr().err)["external_actions"] == "none"

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
                assert node["type"] == "approval", "Customer delivery requires owner review"
                prompt = json.dumps(node, ensure_ascii=False).lower()
                assert "review" in prompt and "before" in prompt
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
