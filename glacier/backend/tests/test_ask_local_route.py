"""Route selection and local-first Ask acceptance tests; all model providers are faked."""
import json
import os
import shutil
import asyncio

from routes import assistant_chat


def _events(response):
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]


def _start(tmp_path, monkeypatch, *, route="auto", codex=True, signed_in=True, ollama=True, answer=None):
    monkeypatch.setenv("GLACIER_ASK_ROUTE", route)
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path / "home"))
    (tmp_path / "home").mkdir(parents=True)
    import routes.assistant_chat as chat
    import system_check

    calls = []
    monkeypatch.setattr(shutil, "which", lambda name: "/fake/codex" if name == "codex" and codex else None)
    monkeypatch.setattr(chat, "_codex_signed_in", lambda: signed_in, raising=False)
    monkeypatch.setattr(chat, "_ollama_answers", lambda: ollama, raising=False)

    def local_chat(prompt, schema=None):
        calls.append(("local", prompt))
        if not ollama:
            raise ConnectionError("fake Ollama is down")
        return answer or {"reply": "Hello from local.", "automation": False}

    monkeypatch.setattr(chat, "_ask_local", local_chat)
    monkeypatch.setattr(chat, "_ask_codex", lambda message: calls.append(("codex", message)) or
                        {"reply": "Hello from Codex.", "automation": False})
    monkeypatch.setattr(system_check, "default_local_model", lambda: "fake-model")
    import vault
    monkeypatch.setattr(vault, "write_note", lambda *args, **kwargs: None)
    return calls


def _chat_events(message):
    response = assistant_chat.chat(assistant_chat.ChatRequest(message=message))
    chunks = asyncio.run(_collect(response.body_iterator))
    return [json.loads(line[6:]) for chunk in chunks for line in chunk.splitlines() if line.startswith("data: ")]


async def _collect(iterator):
    return [chunk async for chunk in iterator]


def test_auto_uses_signed_in_codex(tmp_path, monkeypatch):
    calls = _start(tmp_path, monkeypatch, codex=True, signed_in=True)
    events = _chat_events("Hello")
    assert any(item[0] == "codex" for item in calls)
    assert next(e for e in events if e["type"] == "TEXT_MESSAGE_CONTENT")["delta"] == "Hello from Codex."


def test_auto_uses_local_when_codex_missing(tmp_path, monkeypatch):
    calls = _start(tmp_path, monkeypatch, codex=False, ollama=True)
    events = _chat_events("Hello")
    assert calls[0][0] == "local"
    assert next(e for e in events if e["type"] == "TEXT_MESSAGE_CONTENT")["delta"] == "Hello from local."


def test_auto_with_neither_provider_emits_plain_message(tmp_path, monkeypatch):
    _start(tmp_path, monkeypatch, codex=False, ollama=False)
    events = _chat_events("Hello")
    assert events[-1]["type"] == "RUN_FINISHED"
    message = next(e["delta"] for e in events if e["type"] == "TEXT_MESSAGE_CONTENT")
    assert "Ollama" in message and "Codex" in message


def test_local_route_streams_and_proposes_valid_checked_flow(tmp_path, monkeypatch):
    plan = {"name": "Daily backup", "explanation": "Backs up files each day.", "nodes": [
        {"id": "backup", "type": "command", "config": [{"key": "cmd", "value": "tar -czf backup.tgz data"}]}],
        "edges": [], "acceptance": [{"kind": "human", "question": "Did the backup finish?", "cmd": "", "rubric": ""}]}
    calls = _start(tmp_path, monkeypatch, route="local",
                           answer={"reply": "I can prepare a daily backup.", "automation": True})
    import assistant
    monkeypatch.setattr(assistant, "_ask_local", lambda prompt, schema: plan)
    events = _chat_events("make me a daily backup")
    assert calls[0][0] == "local"
    assert events[0]["type"] == "RUN_STARTED" and events[-1]["type"] == "RUN_FINISHED"
    proposal = json.loads(next(e["delta"] for e in events if e["type"] == "TOOL_CALL_ARGS"))
    assert proposal["flow"]["acceptance"]
    assert proposal["flow"]["nodes"][0]["type"] == "command"


def test_malformed_local_automation_answer_is_friendly(tmp_path, monkeypatch):
    _start(tmp_path, monkeypatch, route="local", answer={"garbage": True})
    events = _chat_events("make me a daily backup")
    assert events[-1]["type"] == "RUN_ERROR"
    assert events[-1]["message"] == "I could not turn that into an automation. Try rephrasing your request."


def test_forced_routes_are_respected_and_settings_explain_choice(tmp_path, monkeypatch):
    import system_check
    calls = _start(tmp_path, monkeypatch, route="local", codex=True)
    settings = system_check.effective_settings(include_ask_route=True)
    assert settings["ask_route"] == "local" and "directly" in settings["ask_route_reason"]
    _chat_events("Hello")
    assert calls[0][0] == "local"

    codex_calls = _start(tmp_path / "codex", monkeypatch, route="codex", codex=True, signed_in=False)
    _chat_events("Hello")
    assert codex_calls[-1][0] == "codex"
