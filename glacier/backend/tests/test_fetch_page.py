import http.server
import socketserver
import threading
import socket

import pytest

import egress
from nodes.fetch_page import NODE


def context(url, allowed_sites="example.org"):
    return {"config": {"url": url, "allowed_sites": allowed_sites}, "prev": None}


def test_server_catalog_lists_fetch_page_once(server):
    catalog = server.get("/api/node-types")
    matches = [item for item in catalog if item["type"] == "fetch_page"]
    assert len(matches) == 1
    assert matches[0]["label"] == "Read a web page"


class Handler(http.server.BaseHTTPRequestHandler):
    body = b"<html><body><h1>Local page</h1></body></html>"
    redirect = None

    def do_GET(self):
        if self.redirect:
            self.send_response(302)
            self.send_header("Location", self.redirect)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *_args):
        pass


def serve(monkeypatch, *, allowed_sites="example.org", body=None, redirect=None):
    handler = type("TestHandler", (Handler,), {"body": body or Handler.body, "redirect": redirect})
    server = socketserver.TCPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    monkeypatch.setattr(egress, "_resolve_public", lambda _host: ["127.0.0.1"])
    return server, thread, f"http://127.0.0.1:{port}/page", "127.0.0.1"


def stop(server, thread):
    server.shutdown()
    thread.join(timeout=2)
    server.server_close()


def test_fetches_allowed_host_and_converts(tmp_path, monkeypatch):
    server, thread, url, allowed = serve(monkeypatch)
    try:
        result = NODE["run"](context(url, allowed))
    finally:
        stop(server, thread)
    assert result["state"] == "done"
    assert "Local page" in result["output"]
    assert "Final URL: http://127.0.0.1:" in result["output"]
    assert "Status: 200" in result["output"]


def test_disallowed_host_refused():
    result = NODE["run"](context("https://not-example.net/", "example.org"))
    assert result["state"] == "failed"
    assert result["output"] == "Add this site to the step's allowed sites first."


@pytest.mark.parametrize("host", ["127.0.0.1", "10.1.2.3", "169.254.1.1", "::1", "fc00::1"])
def test_private_addresses_refused(host):
    if ":" in host:
        url_host = f"[{host}]"
    else:
        url_host = host
    with pytest.raises(PermissionError):
        egress.validate_url(f"http://{url_host}/", {host})


def test_redirect_to_disallowed_host_refused(tmp_path, monkeypatch):
    server, thread, url, allowed = serve(monkeypatch, redirect="https://outside.invalid/")
    try:
        result = NODE["run"](context(url, allowed))
    finally:
        stop(server, thread)
    assert result["state"] == "failed"
    assert "allowed sites" in result["output"]


def test_oversized_body_refused(tmp_path, monkeypatch):
    server, thread, url, allowed = serve(monkeypatch, body=b"x" * (5 * 1024 * 1024 + 1))
    try:
        result = NODE["run"](context(url, allowed))
    finally:
        stop(server, thread)
    assert result["state"] == "failed"
    assert "too large" in result["output"].lower()


def test_bad_scheme_refused():
    result = NODE["run"](context("file:///etc/passwd"))
    assert result["state"] == "failed"
    assert "http or https" in result["output"].lower()


def test_secret_placeholder_refused():
    result = NODE["run"](context("https://example.org/{secret:API_KEY}"))
    assert result["state"] == "failed"
    assert "secret" in result["output"].lower()


def test_output_truncated_at_limit(tmp_path, monkeypatch):
    server, thread, url, allowed = serve(monkeypatch)
    monkeypatch.setattr("nodes.fetch_page._convert_download", lambda *_args: "z" * 20050)
    try:
        result = NODE["run"](context(url, allowed))
    finally:
        stop(server, thread)
    assert result["state"] == "done"
    assert "[Page text truncated.]" in result["output"]
    assert len(result["output"]) <= 20000
