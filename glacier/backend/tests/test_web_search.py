"""Acceptance checks for PH6.4 web search (P-SECURE/P-USABLE).

Drift check: PH6.4; PH6 is parallel-safe and PH3 dependency is at exit. Uses
SearXNG's free, open-source JSON API for a visible, user-configured destination.
Acceptance: local fake server verifies parsed/limited output, missing server,
private-address opt-in, secret rejection, bad JSON, timeout, and 2 MB limit.
"""
import http.server
import json
import socketserver
import threading
import time
from urllib.parse import parse_qs, urlsplit

import pytest

import egress
from nodes.web_search import NODE


def context(server="", **settings):
    return {"config": {"search_server": server, **settings}, "prev": None}


class Handler(http.server.BaseHTTPRequestHandler):
    body = json.dumps({"results": [
        {"title": f"Result {i}", "url": f"https://example.org/{i}", "content": f"Snippet {i}"}
        for i in range(1, 8)
    ]}).encode()
    delay = 0
    redirect = None

    def do_GET(self):
        if self.redirect:
            self.send_response(302)
            self.send_header("Location", self.redirect)
            self.end_headers()
            return
        if self.delay:
            time.sleep(self.delay)
        self.server.query = parse_qs(urlsplit(self.path).query)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *_args):
        pass


def serve(monkeypatch, *, body=None, delay=0, redirect=None):
    handler = type("TestHandler", (Handler,), {"body": body or Handler.body, "delay": delay, "redirect": redirect})
    server = socketserver.TCPServer(("127.0.0.1", 0), handler)
    server.query = None
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(egress, "_resolve_public", lambda _host: ["127.0.0.1"])
    address = f"http://127.0.0.1:{server.server_address[1]}"
    return server, thread, address


def stop(server, thread):
    server.shutdown()
    thread.join(timeout=2)
    server.server_close()


def test_results_parsed_limited_and_sent_as_json_api(monkeypatch):
    server, thread, address = serve(monkeypatch)
    try:
        result = NODE["run"](context(address, query="open source glacier", result_count=3,
                                      allow_private_network=True))
    finally:
        stop(server, thread)
    assert result["state"] == "done"
    assert "Result 1\nhttps://example.org/1\nSnippet 1" in result["output"]
    assert "Result 3" in result["output"]
    assert "Result 4" not in result["output"]
    assert server.query["format"] == ["json"]
    assert server.query["q"] == ["open source glacier"]


def test_missing_server_returns_setup_message():
    result = NODE["run"](context())
    assert result["state"] == "failed"
    assert "SearXNG" in result["output"]
    assert "free and open source" in result["output"].lower()
    assert "https://docs.searxng.org/admin/installation.html" in result["output"]


def test_private_address_refused_by_default():
    result = NODE["run"](context("http://127.0.0.1:8888", query="x"))
    assert result["state"] == "failed"
    assert "private or reserved" in result["output"].lower()


def test_private_address_allowed_only_with_opt_in(monkeypatch):
    server, thread, address = serve(monkeypatch)
    try:
        result = NODE["run"](context(address, query="x", allow_private_network=True))
    finally:
        stop(server, thread)
    assert result["state"] == "done"


def test_private_opt_in_does_not_allow_redirect_to_another_private_host(monkeypatch):
    server, thread, address = serve(monkeypatch, redirect="http://127.0.0.2:8888/search")
    try:
        result = NODE["run"](context(address, query="x", allow_private_network=True))
    finally:
        stop(server, thread)
    assert result["state"] == "failed"
    assert "private or reserved" in result["output"].lower()


def test_secret_placeholder_refused_in_query_and_address():
    query_result = NODE["run"](context("https://search.example", query="{secret:KEY}"))
    address_result = NODE["run"](context("https://{secret:HOST}/", query="x"))
    assert query_result["state"] == address_result["state"] == "failed"
    assert "secret" in query_result["output"].lower()
    assert "secret" in address_result["output"].lower()


def test_bad_json_returns_plain_error(monkeypatch):
    server, thread, address = serve(monkeypatch, body=b"not json")
    try:
        result = NODE["run"](context(address, query="x", allow_private_network=True))
    finally:
        stop(server, thread)
    assert result["state"] == "failed"
    assert "could not read" in result["output"].lower()
    assert "traceback" not in result["output"].lower()


def test_timeout_returns_plain_error(monkeypatch):
    server, thread, address = serve(monkeypatch, delay=10.5)
    try:
        result = NODE["run"](context(address, query="x", allow_private_network=True))
    finally:
        stop(server, thread)
    assert result["state"] == "failed"
    assert "reach" in result["output"].lower()


def test_oversized_response_refused(monkeypatch):
    server, thread, address = serve(monkeypatch, body=b" " * (2 * 1024 * 1024 + 1))
    try:
        result = NODE["run"](context(address, query="x", allow_private_network=True))
    finally:
        stop(server, thread)
    assert result["state"] == "failed"
    assert "2 MB" in result["output"]


@pytest.mark.parametrize("value", ["No", "no", "false", "False", "", "0"])
def test_private_network_needs_an_explicit_yes(value):
    from nodes import web_search
    result = web_search.run({"config": {"search_server": "http://127.0.0.1:9", "query": "x",
                                        "allow_private_network": value}})
    assert result["state"] == "failed"
    assert "private or reserved network" in result["output"]
