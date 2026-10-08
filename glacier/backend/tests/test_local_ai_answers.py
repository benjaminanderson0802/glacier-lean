import json
import importlib.util
from pathlib import Path

import decider
from nodes import local_ai


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def read(self):
        return json.dumps(self.payload).encode()


def _stub_ollama(monkeypatch, content):
    calls = []

    def urlopen(request, timeout):
        body = json.loads(request.data)
        calls.append((request.full_url, body, timeout))
        return _Response({"message": {"content": content}, "prompt_eval_count": 4, "eval_count": 3,
                          "eval_duration": 1_000_000_000})

    monkeypatch.setattr(local_ai.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(decider.urllib.request, "urlopen", urlopen)
    monkeypatch.setenv("GLACIER_OLLAMA_URL", "http://ollama.test")
    return calls


def _ctx(config):
    return {"config": {"prompt": "Compute 19 + 23", **config}, "env_id": "e", "run_id": "r"}


def test_answer_only_sends_system_message_zero_temperature_and_strips_allowed_wrappers(monkeypatch):
    calls = _stub_ollama(monkeypatch, "  **42.**  ")
    result = local_ai.run(_ctx({"answer_style": "Answer only"}))

    assert calls[0][1]["messages"] == [
        {"role": "system", "content": "Reply with only the answer. No explanation, no labels, no markdown, no extra words."},
        {"role": "user", "content": "Compute 19 + 23"},
    ]
    assert calls[0][1]["options"] == {"temperature": 0}
    assert calls[0][1]["think"] is False
    assert result["output"] == "42"


def test_answer_only_strips_only_listed_cases(monkeypatch):
    cases = {
        " `42` ": "42",
        "**42**": "42",
        "42.": "42",
        "Answer: 42.": "Answer: 42",
        "42.\n": "42.",
        "42!": "42!",
        "**42** more": "**42** more",
        "``42``": "``42``",
    }
    for raw, expected in cases.items():
        _stub_ollama(monkeypatch, raw)
        assert local_ai.run(_ctx({"answer_style": "Answer only"}))["output"] == expected


def test_free_text_keeps_request_and_reply_behavior(monkeypatch):
    calls = _stub_ollama(monkeypatch, "  Here is the answer: **42**.  ")
    result = local_ai.run(_ctx({"answer_style": "Free text"}))

    assert calls[0][1]["messages"] == [{"role": "user", "content": "Compute 19 + 23"}]
    assert "options" not in calls[0][1]
    assert result["output"] == "  Here is the answer: **42**.  "


def test_default_style_is_answer_only(monkeypatch):
    calls = _stub_ollama(monkeypatch, "42")
    local_ai.run(_ctx({}))
    assert calls[0][1]["options"] == {"temperature": 0}
    assert calls[0][1]["messages"][0]["role"] == "system"
    fields = {field["key"]: field for field in local_ai.NODE["catalog"]["fields"]}
    assert fields["answer_style"]["default"] == "Answer only"
    assert fields["answer_style"]["options"] == ["Answer only", "Free text"]


def test_choose_one_sends_json_enum_and_returns_selected_option(monkeypatch):
    calls = _stub_ollama(monkeypatch, '{"labels":["billing","technical"]}')
    result = local_ai.run(_ctx({"choose_one": "billing, technical, sales"}))

    body = calls[0][1]
    assert "Choose one of: billing, technical, sales." in body["messages"][-1]["content"]
    assert body["format"] == {"type": "object", "properties": {"labels": {
        "type": "array", "items": {"type": "string", "enum": ["billing", "technical", "sales"]},
        "minItems": 1, "maxItems": 100}}, "required": ["labels"], "additionalProperties": False}
    assert result["output"] == "billing\ntechnical"
    assert {field["key"]: field for field in local_ai.NODE["catalog"]["fields"]}["choose_one"]


def test_choose_one_rejects_malformed_model_reply(monkeypatch):
    _stub_ollama(monkeypatch, '{"labels":"technical"}')
    try:
        local_ai.run(_ctx({"choose_one": "billing, technical"}))
    except ValueError as exc:
        assert str(exc) == "Ollama returned a choice outside the allowed options"
    else:
        raise AssertionError("invalid constrained response should be rejected")


def test_benchmark_uses_real_local_ai_node_with_fake_ollama(monkeypatch):
    path = Path(__file__).resolve().parents[3] / "bench/local_models/run_eval.py"
    spec = importlib.util.spec_from_file_location("local_models_run_eval", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    calls = _stub_ollama(monkeypatch, "42")
    result = module.evaluate_task({"id": "add", "prompt": "Compute 19 + 23", "expected": "42"}, "fake-model")

    assert result["passed"] is True
    assert result["output"] == "42"
    assert calls[0][1]["model"] == "fake-model"
