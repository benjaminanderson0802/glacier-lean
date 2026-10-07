"""Acceptance tests for preferring a second-machine gateway route when it is online."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import gateway


class FakeOpenAI:
    def __init__(self, content):
        self.content = content
        self.requests = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                owner.requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                body = json.dumps({"model": "fake", "choices": [{"message": {"content": owner.content}}]}).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}/v1"

    def close(self):
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()


def _ctx(home):
    return {"home": str(home), "config": {"prompt": "hello"}, "env_id": "test", "run_id": "run1"}


def _routes(laptop, local):
    return [
        {"name": "laptop", "base_url": laptop.base_url, "model": "laptop-model", "paid": False,
         "prefer_when_online": True, "health_url": laptop.base_url.replace("/v1", "/api/tags")},
        {"name": "local", "base_url": local.base_url, "model": "local-model", "paid": False},
    ]


def test_online_preferred_route_answers_before_local(tmp_path, monkeypatch):
    laptop = FakeOpenAI("laptop answer")
    local = FakeOpenAI("local answer")
    probes = []
    try:
        monkeypatch.setattr(gateway, "_health_cache", {})
        monkeypatch.setattr(gateway, "_probe_health", lambda url: probes.append(url) or True)
        result = gateway.complete(_ctx(tmp_path), routes=_routes(laptop, local))
        assert result["state"] == "done" and result["output"] == "laptop answer"
        assert result["usage"]["route"] == "gateway/laptop"
        assert len(laptop.requests) == 1 and not local.requests
        assert probes == ["http://127.0.0.1:%s/api/tags" % laptop.server.server_port]
    finally:
        laptop.close()
        local.close()


def test_offline_preferred_route_falls_back_and_usage_names_local(tmp_path, monkeypatch, caplog):
    laptop = FakeOpenAI("unused")
    local = FakeOpenAI("local answer")
    try:
        monkeypatch.setattr(gateway, "_health_cache", {})
        monkeypatch.setattr(gateway, "_probe_health", lambda _url: False)
        result = gateway.complete(_ctx(tmp_path), routes=_routes(laptop, local))
        assert result["state"] == "done" and result["output"] == "local answer"
        assert result["usage"]["route"] == "gateway/local"
        assert not laptop.requests and len(local.requests) == 1
        assert "laptop" in caplog.text and "offline" in caplog.text.lower()
        warning_count = caplog.text.count("Skipping preferred model route laptop because it is offline")
        assert warning_count == 1
        gateway.complete(_ctx(tmp_path), routes=_routes(laptop, local))
        assert caplog.text.count("Skipping preferred model route laptop because it is offline") == warning_count
    finally:
        laptop.close()
        local.close()


def test_preferred_route_health_is_cached_for_30_seconds(tmp_path, monkeypatch):
    laptop = FakeOpenAI("laptop answer")
    local = FakeOpenAI("unused")
    clock = [100.0]
    probes = []
    try:
        monkeypatch.setattr(gateway, "_health_cache", {})
        monkeypatch.setattr(gateway, "_probe_health", lambda _url: probes.append(True) or True)
        monkeypatch.setattr(gateway.time, "monotonic", lambda: clock[0])
        routes = _routes(laptop, local)
        assert gateway.complete(_ctx(tmp_path), routes=routes)["usage"]["route"] == "gateway/laptop"
        assert gateway.complete(_ctx(tmp_path), routes=routes)["usage"]["route"] == "gateway/laptop"
        assert len(probes) == 1
        clock[0] += 31
        assert gateway.complete(_ctx(tmp_path), routes=routes)["usage"]["route"] == "gateway/laptop"
        assert len(probes) == 2
    finally:
        laptop.close()
        local.close()


def test_route_status_uses_plain_language_and_cached_health(monkeypatch):
    monkeypatch.setattr(gateway, "_health_cache", {})
    monkeypatch.setattr(gateway, "_probe_health", lambda _url: True)
    status = gateway.route_status([
        {"name": "laptop", "paid": False, "prefer_when_online": True, "health_url": "http://laptop/api/tags"},
        {"name": "hosted", "paid": True},
        {"name": "local", "paid": False},
    ])
    assert status == [
        {"name": "laptop", "status": "Online and preferred"},
        {"name": "hosted", "status": "Needs approval before use"},
        {"name": "local", "status": "Available when earlier routes cannot answer"},
    ]


def test_preferred_route_without_explicit_free_flag_is_refused(tmp_path, monkeypatch):
    filed = []
    monkeypatch.setattr(gateway.claims, "file_claim", lambda **kwargs: filed.append(kwargs) or {"id": "claim"})
    monkeypatch.setattr(gateway.claims, "list_claims", lambda status=None: [])
    preferred = {"name": "laptop", "base_url": "http://127.0.0.1:1/v1", "model": "unknown",
                 "prefer_when_online": True, "health_url": "http://127.0.0.1:1/api/tags"}
    result = gateway.complete(_ctx(tmp_path), routes=[preferred])
    assert result["state"] == "failed"
    assert result["output"] == gateway.FRIENDLY_FAILURE
    assert len(filed) == 1 and filed[0]["kind"] == "policy"
