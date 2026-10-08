import http.server
import json
import socketserver
import threading

import keyring
import pytest

import egress
import secrets_store
from nodes.http_request import NODE


def test_catalog_marks_changing_methods():
    assert NODE["catalog"]["changing_methods"] == ["POST", "PUT", "PATCH", "DELETE"]


class MemoryKeyring(keyring.backend.KeyringBackend):
    priority = 1

    def __init__(self):
        self.values = {}

    def get_password(self, service, username):
        return self.values.get((service, username))

    def set_password(self, service, username, password):
        self.values[(service, username)] = password

    def delete_password(self, service, username):
        del self.values[(service, username)]


class Handler(http.server.BaseHTTPRequestHandler):
    requests = []
    status = 200
    body = b"ok"
    redirect = None

    def _serve(self):
        data = self.rfile.read(int(self.headers.get("Content-Length", 0))) if self.command in {"POST", "PUT", "PATCH", "DELETE"} else b""
        type(self).requests.append((self.command, dict(self.headers), data))
        if self.redirect:
            self.send_response(302)
            self.send_header("Location", self.redirect)
            self.end_headers()
            return
        self.send_response(self.status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(self.body)

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = _serve

    def log_message(self, *_args):
        pass


@pytest.fixture
def local_api(monkeypatch):
    Handler.requests = []
    Handler.status = 200
    Handler.body = b'{"ok": true}'
    Handler.redirect = None
    server = socketserver.TCPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(egress, "_resolve_public", lambda _host: ["127.0.0.1"])
    yield f"http://127.0.0.1:{server.server_address[1]}/api"
    server.shutdown()
    thread.join(timeout=2)
    server.server_close()


def ctx(url, **config):
    return {"config": {"url": url, "allowed_sites": "127.0.0.1", **config},
            "prev": {"output": "prior text"}}


@pytest.mark.parametrize("method", ["GET", "POST", "PUT", "PATCH", "DELETE"])
def test_each_http_method_is_sent(local_api, method):
    result = NODE["run"](ctx(local_api, method=method, allow_private_network="Yes"))
    assert result["state"] == "done", result
    assert Handler.requests[-1][0] == method


def test_json_body_expands_previous_output(local_api):
    result = NODE["run"](ctx(local_api, method="POST", body='{"message":"{prev_output}"}',
                             body_type="JSON", allow_private_network="Yes"))
    assert result["state"] == "done", result
    assert json.loads(Handler.requests[-1][2]) == {"message": "prior text"}


def test_secret_header_is_sent_and_redacted_everywhere(local_api, monkeypatch, tmp_path):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    keyring.set_keyring(MemoryKeyring())
    keyring.set_password(secrets_store.SERVICE, "api", "super-secret-value")
    secrets_store._write_names(["api"])
    Handler.body = b"received super-secret-value"
    result = NODE["run"](ctx(local_api, headers="Authorization: Bearer {secret:api}", allow_private_network="Yes"))
    assert Handler.requests[-1][1]["Authorization"] == "Bearer super-secret-value"
    assert "super-secret-value" not in result["output"]
    assert "[secret api]" in result["output"]


def test_secret_placeholder_in_url_refused():
    result = NODE["run"](ctx("https://example.org/{secret:api}"))
    assert result["state"] == "failed"
    assert "secret" in result["output"].lower()


def test_redirect_to_another_site_refused(local_api):
    Handler.redirect = "https://outside.invalid/"
    result = NODE["run"](ctx(local_api, allow_private_network="Yes"))
    assert result["state"] == "failed"
    assert "allowed sites" in result["output"].lower()


def test_private_address_requires_yes(local_api):
    result = NODE["run"](ctx(local_api, allow_private_network="No"))
    assert result["state"] == "failed"
    assert "private" in result["output"].lower()


def test_resolves_and_connects_to_the_checked_dns_address(local_api, monkeypatch):
    host_url = local_api.replace("127.0.0.1", "api.example.org")
    monkeypatch.setattr("nodes.http_request._resolve", lambda host, _allow_private: ["127.0.0.1"]
                        if host == "api.example.org" else pytest.fail(f"Unexpected DNS lookup for {host}"))
    result = NODE["run"]({"config": {"url": host_url, "allowed_sites": "api.example.org",
                                      "allow_private_network": "Yes"}, "prev": None})
    assert result["state"] == "done", result
    assert "ok" in result["output"]


def test_large_response_is_capped(local_api):
    Handler.body = b"x" * (1024 * 1024 + 1)
    result = NODE["run"](ctx(local_api, allow_private_network="Yes"))
    assert result["state"] == "done"
    assert len(result["output"]) <= 20000
    assert "truncated" in result["output"].lower()


def test_unexpected_status_fails(local_api):
    Handler.status = 503
    result = NODE["run"](ctx(local_api, allow_private_network="Yes"))
    assert result["state"] == "failed"
    assert "503" in result["output"]
