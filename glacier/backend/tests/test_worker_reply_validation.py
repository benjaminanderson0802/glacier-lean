"""Unit regressions for worker response parsing; independent acceptance stays unchanged."""
import json

import pytest

import gateway
from nodes import local_ai


class Reply:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def read(self):
        return json.dumps(self.payload).encode()


def test_gateway_default_uses_owner_selected_granite(tmp_path):
    assert gateway.routes(tmp_path)[0]["model"] == "granite3.3:2b"


@pytest.mark.parametrize("payload", [None, [], {}, {"choices": []},
    {"choices": [None]}, {"choices": [{"message": None}]},
    {"choices": [{"message": {"content": " "}}]},
    {"choices": [{"message": {"content": "answer"}}], "usage": []},
    {"choices": [{"message": {"content": "answer"}}], "usage": {"prompt_tokens": "bad"}},
])
def test_invalid_gateway_reply_uses_next_route(tmp_path, monkeypatch, payload):
    requests = []

    def respond(request, timeout):
        requests.append(request.full_url)
        return Reply(payload if len(requests) == 1 else {
            "choices": [{"message": {"content": "fallback answer"}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 2},
        })

    monkeypatch.setattr(gateway, "open_model_request", respond)
    routes = [{"name": name, "base_url": f"http://localhost/{name}",
               "model": "granite3.3:2b", "paid": False} for name in ("bad", "good")]
    result = gateway.complete({"home": tmp_path, "config": {"prompt": "hello"}}, routes=routes)
    assert result["state"] == "done"
    assert result["output"] == "fallback answer"
    assert result["usage"]["route"] == "gateway/good"
    assert result["usage"]["tokens_in"] == 5
    assert "bad" not in json.loads((tmp_path / "gateway_usage.json").read_text())


@pytest.mark.parametrize("payload", [None, [], {}, {"message": []},
    {"message": {"content": " "}}, {"message": {"content": 42}},
    {"message": {"content": "ok"}, "eval_count": "bad"},
])
def test_invalid_local_reply_fails_cleanly(monkeypatch, payload):
    monkeypatch.setattr(local_ai, "open_model_request", lambda *a, **k: Reply(payload))
    result = local_ai.run({"config": {"prompt": "hello", "model": "granite3.3:2b"},
                           "env_id": "e", "run_id": "r"})
    assert result["state"] == "failed" and result["exit_code"] != 0
    assert "invalid reply" in result["output"]
