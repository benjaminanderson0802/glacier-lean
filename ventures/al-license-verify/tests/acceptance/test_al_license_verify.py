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
        found_socketpair |= (
            frame.f_code.co_name == "socketpair" and filename.endswith("/socket.py")
        ) or (
            frame.f_code.co_name in {"socketpair", "_socketpair"}
            and filename.endswith("/asyncio/windows_utils.py")
        )
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


def test_windows_asyncio_socketpair_connect_is_allowed(monkeypatch):
    calls = []
    monkeypatch.setattr(
        sys.modules[__name__],
        "_ORIGINAL_SOCKET_CONNECT",
        lambda sock, address: calls.append(address),
    )
    namespace = {"_blocked_connect": _blocked_connect}
    exec(
        compile(
            "def socketpair(sock, address):\n"
            "    return _blocked_connect(sock, address)\n",
            "C:/Python/Lib/asyncio/windows_utils.py",
            "exec",
        ),
        namespace,
    )

    with socket.socket() as sock:
        namespace["socketpair"](sock, ("127.0.0.1", 43210))

    assert calls == [("127.0.0.1", 43210)]


def uncertain(value):
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    return "uncertain - please check" in text.replace("—", "-").replace("–", "-").lower()


def csv_file(path, fields, rows, delimiter=","):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)
    return path


api = load_module(KIT / "scripts/verify.py", "accept_license")
DOC_URL = "https://genconbd.alabama.gov/"
DOC_MARKER = "License Roster"
ROSTER = "License Number,Name,Status,Expiration Date,Specialty\n54321,Synthetic Building LLC,Active,12/31/2026,Building Construction\n"

def lookup(roster, query, as_of="2026-10-09"):
    return api.lookup_many(roster=roster, queries=[query], roster_as_of=as_of,
        source_url=DOC_URL, checked_at="2026-10-10T12:00:00+00:00")[0]

def test_exact_match_preserves_supplied_status():
    result = lookup(api.load_roster_text(ROSTER), {"license_number": "54321"})
    assert result["outcome"] == "match"
    assert result["expiration_date"] == "2026-12-31"
    assert "not a real-time license determination" in result["limitations"]

def test_absence_uses_snapshot_date_not_lookup_date():
    result = lookup(api.load_roster_text(ROSTER), {"license_number": "99999"})
    assert result["outcome"] == "no match found in supplied Alabama roster as of 2026-10-09"
    assert result["status"] is None

@pytest.mark.parametrize("case", ["stale", "duplicate", "missing_key"])
def test_ambiguous_or_partial_roster_uncertain(case):
    roster = api.load_roster_text(ROSTER)
    as_of = "2020-01-01" if case == "stale" else "2026-10-09"
    if case == "duplicate":
        roster *= 2
    if case == "missing_key":
        roster = [{"business_name": "Synthetic Building LLC"}]
    assert uncertain(lookup(roster, {"license_number": "54321"}, as_of))

def test_unicode_names_do_not_collapse_to_empty_matching_key():
    roster = api.load_roster_text("License Number,Name\n54321,李氏建设\n")
    assert lookup(roster, {"name": "李氏建设"})["outcome"] == "match"
    result = lookup(roster, {"name": "王氏建工"})
    assert result["outcome"] != "match", "Different Unicode names were treated as identical"

@pytest.mark.parametrize("body", ["", "wrong,columns\na,b\n", "License Number,Name\n"])
def test_empty_malformed_roster_rejected(body):
    with pytest.raises(ValueError):
        api.load_roster_text(body)

def test_invalid_expiry_is_not_verified_fact():
    roster = api.load_roster_text(ROSTER.replace("12/31/2026", "not-a-date"))
    result = lookup(roster, {"license_number": "54321"})
    assert uncertain(result) or result["expiration_date"] is None

@pytest.mark.parametrize("url", ["https://genconbd.alabama.gov/search/", "http://api.apify.com/file", "https://example.com/roster.csv", "file:///etc/passwd"])
def test_no_board_scraping_or_arbitrary_fetch(url):
    with pytest.raises(ValueError):
        api.read_roster_file(url)

@pytest.mark.parametrize("code", [429, 503])
def test_upload_outage_rate_limit_classified(monkeypatch, code):
    def unavailable(*args, **kwargs):
        raise HTTPError("https://api.apify.com/v2/key-value-stores/test/records/roster", code, "unavailable", {}, None)
    monkeypatch.setattr(api, "urlopen", unavailable)
    with pytest.raises(api.SourceUnavailable):
        api.read_roster_file("https://api.apify.com/v2/key-value-stores/test/records/roster")

@pytest.fixture
def actor(monkeypatch):
    import types
    from datetime import date
    class FakeActor:
        def __init__(self):
            self.rows, self.charges, self.status = [], [], []
            self.input = {"queries": [{"license_number": "54321"}],
                "roster_file": "https://api.apify.com/v2/key-value-stores/test/records/roster",
                "roster_as_of": date.today().isoformat(), "source_url": DOC_URL}
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return False
        async def get_input(self): return self.input
        async def push_data(self, result): self.rows.append(result)
        async def charge(self, **kwargs): self.charges.append(kwargs)
        async def set_status_message(self, message, **kwargs): self.status.append(message)
    fake = FakeActor()
    monkeypatch.setitem(sys.modules, "apify", types.SimpleNamespace(Actor=fake))
    package = types.ModuleType("scripts")
    package.__path__ = [str(KIT / "scripts")]
    monkeypatch.setitem(sys.modules, "scripts", package)
    monkeypatch.setitem(sys.modules, "scripts.verify", api)
    wrapper = load_module(KIT / "src/__main__.py", "accept_actor")
    monkeypatch.setattr(wrapper, "read_roster_file", lambda _: ROSTER)
    monkeypatch.setenv("APIFY_IS_AT_HOME", "1")
    monkeypatch.delenv("ACTOR_TEST_PAY_PER_EVENT", raising=False)
    return wrapper, fake

def test_mock_actor_completed_lookup_charges_once(actor):
    import asyncio
    wrapper, fake = actor
    asyncio.run(wrapper.main())
    assert len(fake.rows) == len(fake.charges) == 1
    assert fake.charges[0]["event_name"] == "license-lookup"
    assert fake.charges[0]["count"] == 1
    assert fake.charges[0]["idempotency_key"]

def test_mock_actor_local_mode_never_charges(actor, monkeypatch):
    import asyncio
    wrapper, fake = actor
    monkeypatch.setenv("APIFY_IS_AT_HOME", "0")
    asyncio.run(wrapper.main())
    assert fake.rows and fake.charges == []

def test_mock_actor_uncertain_never_charges(actor):
    import asyncio
    wrapper, fake = actor
    fake.input["roster_as_of"] = "2020-01-01"
    asyncio.run(wrapper.main())
    assert uncertain(fake.rows[0]) and fake.charges == []

@pytest.mark.parametrize("code", [429, 503])
def test_mock_actor_outage_only_never_charges(actor, monkeypatch, code):
    import asyncio
    wrapper, fake = actor
    def unavailable(_): raise api.SourceUnavailable(f"HTTP {code}")
    monkeypatch.setattr(wrapper, "read_roster_file", unavailable)
    try:
        asyncio.run(wrapper.main())
    except api.SourceUnavailable:
        pass
    assert fake.rows == [] and fake.charges == []

@pytest.mark.parametrize("code", [429, 503])
def test_mock_actor_outage_has_customer_uncertainty(actor, monkeypatch, code):
    import asyncio
    wrapper, fake = actor
    def unavailable(_): raise api.SourceUnavailable(f"HTTP {code}")
    monkeypatch.setattr(wrapper, "read_roster_file", unavailable)
    try:
        asyncio.run(wrapper.main())
    except api.SourceUnavailable:
        pass
    assert uncertain(fake.rows + fake.status), "Actor aborts without customer-facing uncertain result"

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
                assert "send the draft pitch yourself" in prompt and "nothing is sent by glacier" in prompt
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
