"""Per-install access token: the engine refuses API calls that don't come from the Glacier app."""
import os
import stat
import subprocess
import sys

import pytest
from conftest import TEST_TOKEN, raw_httpx, raw_ws_connect
from websockets.exceptions import InvalidStatus, ConnectionClosed
from websockets.sync.client import connect as ws_connect
from log_redaction import RedactWebSocketToken
import logging

NOT_OURS = "This request isn't from your Glacier app."


def test_api_needs_the_token(server):
    missing = raw_httpx["get"](server.url + "/api/environments", timeout=30)
    assert missing.status_code == 401 and missing.json()["detail"] == NOT_OURS
    wrong = raw_httpx["get"](server.url + "/api/environments", headers={"Authorization": "Bearer nope"}, timeout=30)
    assert wrong.status_code == 401
    right = raw_httpx["get"](server.url + "/api/environments", headers={"Authorization": f"Bearer {TEST_TOKEN}"}, timeout=30)
    assert right.status_code == 200


def test_cookie_does_not_authenticate_api(server):
    response = raw_httpx["get"](server.url + "/api/environments",
                                 headers={"Cookie": f"glacier-token={TEST_TOKEN}"}, timeout=30)
    assert response.status_code == 401
    assert response.json()["detail"] == NOT_OURS


def test_token_extraction_supports_proxy_authorization_and_websocket_protocol():
    import local_token

    assert local_token.from_headers_or_protocol({"authorization": f"Bearer {TEST_TOKEN}"}) == TEST_TOKEN
    assert local_token.from_headers_or_protocol({"sec-websocket-protocol": f"glacier-events, {TEST_TOKEN}"}) == TEST_TOKEN
    assert local_token.from_headers_or_protocol({"cookie": f"glacier-token={TEST_TOKEN}"}) is None


def test_state_changing_call_without_token_changes_nothing(server):
    env = {"id": "sneaky", "name": "sneaky", "nodes": [], "edges": []}
    assert raw_httpx["put"](server.url + "/api/environments/sneaky", json=env, timeout=30).status_code == 401
    assert all(e["id"] != "sneaky" for e in server.get("/api/environments"))


def test_health_is_open_and_has_no_data(server):
    r = raw_httpx["get"](server.url + "/api/health", timeout=30)
    assert r.status_code == 200 and r.json() == {"ok": True}


def test_preflight_passes_without_token(server):
    r = raw_httpx["options"](server.url + "/api/environments", timeout=30,
                             headers={"Origin": "http://tauri.localhost", "Access-Control-Request-Method": "GET",
                                      "Access-Control-Request-Headers": "authorization"})
    assert r.status_code == 200


def test_websocket_needs_the_token(server):
    url = server.url.replace("http", "ws") + "/api/events"
    with pytest.raises((InvalidStatus, ConnectionClosed)):
        with ws_connect(url + "?token=wrong") as ws:
            ws.recv(timeout=2)
    with ws_connect(url + "?token=" + TEST_TOKEN) as ws:  # accepted
        pass


def test_websocket_protocol_auth_rejects_missing_and_wrong_token(server):
    url = server.url.replace("http", "ws") + "/api/events"
    for protocols in (None, ["glacier-events", "wrong"]):
        with pytest.raises((InvalidStatus, ConnectionClosed)):
            with raw_ws_connect(url, subprotocols=protocols) as ws:
                ws.recv(timeout=2)
    with raw_ws_connect(url, subprotocols=["glacier-events", TEST_TOKEN]) as ws:
        pass


def test_websocket_access_log_redacts_query_token(server):
    url = server.url.replace("http", "ws") + "/api/events?token=super-secret-query-token"
    with pytest.raises((InvalidStatus, ConnectionClosed)):
        with ws_connect(url) as ws:
            ws.recv(timeout=2)
    log = server.diagnostics()
    assert "super-secret-query-token" not in log
    assert '"WebSocket /api/events" 403' in log


def test_access_log_filter_redacts_query_token():
    record = logging.LogRecord("uvicorn.access", logging.INFO, "", 0,
                               'WebSocket /api/events?token=secret - "client" 403', (), None)
    assert RedactWebSocketToken().filter(record)
    assert record.getMessage() == 'WebSocket /api/events?token=[redacted] - "client" 403'


def test_token_file_created_owner_only(tmp_path):
    env = dict(os.environ, GLACIER_HOME=str(tmp_path))
    env.pop("GLACIER_TOKEN", None)
    code = "import local_token; print(local_token.get_token()); print(local_token.get_token())"
    out = subprocess.run([sys.executable, "-c", code], cwd=os.path.dirname(os.path.dirname(__file__)), env=env,
                         capture_output=True, text=True, check=True).stdout.split()
    assert len(out) == 2 and out[0] == out[1] and len(out[0]) == 64  # stable across reads, 32 random bytes
    path = tmp_path / ".engine-token"
    assert path.read_text().strip() == out[0]
    if os.name != "nt":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
