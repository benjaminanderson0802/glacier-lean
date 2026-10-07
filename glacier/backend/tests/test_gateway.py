import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import claims
import gateway
from nodes import ai_any


class FakeOpenAI:
    def __init__(self, content="answer", model="fake-model", tokens=(7, 3)):
        self.requests = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                owner.requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                body = json.dumps({"model": model, "choices": [{"message": {"content": content}}],
                                   "usage": {"prompt_tokens": tokens[0], "completion_tokens": tokens[1]}}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}/v1"

    def close(self):
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()


def ctx(home, config, prev=None):
    return {"home": str(home), "config": config, "env_id": "test", "run_id": "run1", "node_id": "ai",
            "prev": prev, "memory": lambda task: ""}


def test_falls_back_in_order_and_records_answering_route(tmp_path):
    second = FakeOpenAI(content="from second", model="model-b", tokens=(11, 5))
    try:
        routes = [{"name": "down", "base_url": "http://127.0.0.1:1/v1", "model": "a", "paid": False},
                  {"name": "second", "base_url": second.base_url, "model": "b", "paid": False}]
        result = gateway.complete(ctx(tmp_path, {"prompt": "hello {env} {run}"}), routes=routes)
        assert result["state"] == "done" and result["output"] == "from second"
        assert result["usage"] == {"model": "model-b", "route": "gateway/second", "tokens_in": 11,
                                   "tokens_out": 5, "cost_usd": 0.0}
        assert second.requests[0]["messages"][0]["content"] == "hello test run1"
    finally:
        second.close()


def test_daily_cap_skips_route(tmp_path):
    capped = FakeOpenAI(content="should not be used")
    available = FakeOpenAI(content="available")
    try:
        routes = [{"name": "capped", "base_url": capped.base_url, "model": "a", "paid": False, "daily_request_cap": 1},
                  {"name": "available", "base_url": available.base_url, "model": "b", "paid": False}]
        for index in range(2):
            result = gateway.complete(ctx(tmp_path, {"prompt": "hello"}), routes=routes)
            assert result["state"] == "done"
            assert result["usage"]["route"] == ("gateway/capped" if index == 0 else "gateway/available")
        assert len(capped.requests) == 1 and len(available.requests) == 1
    finally:
        capped.close()
        available.close()


def test_paid_only_route_is_refused_and_policy_claim_filed(tmp_path, monkeypatch):
    filed = []
    monkeypatch.setattr(gateway.claims, "file_claim", lambda **kw: filed.append(kw) or {"id": "claim"})
    existing = []
    monkeypatch.setattr(gateway.claims, "list_claims", lambda status=None: [
        {"kind": "policy", "summary": "Paid model route needs owner approval", "status": "filed",
         "updated": gateway.datetime.now(gateway.timezone.utc).isoformat()}
    ] if existing else [])
    route = {"name": "paid", "base_url": "http://127.0.0.1:1/v1", "model": "paid", "paid": True}
    missing_paid = {"name": "unspecified", "base_url": "http://127.0.0.1:2/v1", "model": "unknown"}
    for _ in range(2):
        result = gateway.complete(ctx(tmp_path, {"prompt": "hello"}), routes=[route, missing_paid])
        assert result["state"] == "failed"
        assert result["output"] == "No free model is available right now. A paid option needs your approval (a claim was filed)."
        existing.append(True)
    assert len(filed) == 1 and filed[0]["kind"] == "policy"


def test_gateway_settings_validation_is_friendly(tmp_path):
    (tmp_path / "gateway.json").write_text("{broken", encoding="utf-8")
    result = gateway.complete(ctx(tmp_path, {"prompt": "hello"}))
    assert result["state"] == "failed"
    assert result["output"].startswith("Your model settings file (gateway.json) can't be read:")

    (tmp_path / "gateway.json").write_text(json.dumps([{"name": "missing-fields"}]), encoding="utf-8")
    result = gateway.complete(ctx(tmp_path, {"prompt": "hello"}))
    assert result["state"] == "failed"
    assert result["output"].startswith("Your model settings file (gateway.json) can't be read:")


def test_all_free_routes_down_has_friendly_failure(tmp_path):
    routes = [{"name": "one", "base_url": "http://127.0.0.1:1/v1", "model": "a", "paid": False},
              {"name": "two", "base_url": "http://127.0.0.1:2/v1", "model": "b", "paid": False}]
    result = gateway.complete(ctx(tmp_path, {"prompt": "hello"}), routes=routes)
    assert result["state"] == "failed"
    assert "No free model is available right now" in result["output"]


def test_ai_any_catalog_and_placeholder_expansion(tmp_path):
    server = FakeOpenAI()
    try:
        result = ai_any.run(ctx(tmp_path, {"prompt": "{env}/{run}: {prev_output}"}, {"output": "prior"}),
                            routes=[{"name": "one", "base_url": server.base_url, "model": "x", "paid": False}])
        assert result["state"] == "done"
        assert server.requests[0]["messages"][0]["content"] == "test/run1: prior"
        assert ai_any.NODE["catalog"]["type"] == "ai_any"
        assert ai_any.NODE["catalog"]["label"] == "AI (any model)"
        assert ai_any.NODE["catalog"]["worker"] is True
    finally:
        server.close()
