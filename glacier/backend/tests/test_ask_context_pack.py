"""Acceptance checks for the shared, bounded Ask context and engine adapters."""
import json
import asyncio
import pytest

import vault
from routes import assistant_chat


def _events(response):
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]


async def _collect(iterator):
    return [chunk async for chunk in iterator]


def _chat(message="What is Glacier?", conversation_id=None):
    response = assistant_chat.chat(assistant_chat.ChatRequest(message=message, conversation_id=conversation_id))
    chunks = asyncio.run(_collect(response.body_iterator))
    return [json.loads(line[6:]) for chunk in chunks for line in chunk.splitlines() if line.startswith("data: ")]


def _prepare(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("GLACIER_ASK_ROUTE", "codex")
    monkeypatch.setenv("GLACIER_ASK_REMEMBER_CHATS", "true")
    (tmp_path / "home").mkdir()
    vault.init(str(tmp_path / "vault"))
    monkeypatch.setattr(assistant_chat.ask_context, "_system_state", lambda engine="", model=None: f"Current system state: Ask currently uses {engine} ({model}); Codex signed in; Ollama model fake:latest; no active flows")
    import secrets_store
    monkeypatch.setattr(secrets_store, "redact", lambda value: value.replace("private-token-123", "[secret API_KEY]"))


def test_context_pack_is_shared_bounded_personalized_and_redacted(tmp_path, monkeypatch):
    _prepare(tmp_path, monkeypatch)
    import secrets_store
    monkeypatch.setattr(secrets_store, "redact", lambda value: value.replace("private-token-123", "[secret API_KEY]"))
    import memory_context
    monkeypatch.setattr(memory_context, "find", lambda *_a, **_kw: ["notes/pref.md"])
    vault.write_note("notes/about-me.md", "# About me\nI like concise answers and call the owner Ben.", agent="owner")
    vault.write_note("notes/pref.md", "# Preferences\nPlease use short practical steps.", agent="owner")
    pack = assistant_chat.ask_context.build("create a flow", engine="codex", model="granite3.3:2b")
    assert "Glacier" in pack
    assert all(tab in pack for tab in ("Home:", "Ask:", "Automations:", "Memory:", "Settings:"))
    assert "Approve" in pack
    assert "Codex signed in" in pack
    assert "codex (granite3.3:2b)" in pack
    assert "Ben" in pack or "concise answers" in pack
    assert "short practical steps" in pack
    assert "Preferences" in pack or "Relevant notes" in pack
    assert "private-token-123" not in pack
    assert len(pack) <= assistant_chat.ask_context.character_limit("granite3.3:2b")
    assert assistant_chat.ask_context.character_limit("granite3.3:2b") < assistant_chat.ask_context.character_limit("model-12b")


def test_disabled_previous_chats_are_absent_from_pack(tmp_path, monkeypatch):
    _prepare(tmp_path, monkeypatch)
    (tmp_path / "home" / "settings.json").write_text(json.dumps({"ask_remember_previous_chats": False}), encoding="utf-8")
    conversation_id = "a" * 36
    assistant_chat._append_conversation(conversation_id, "CHAT_HISTORY_SENTINEL", "old response")
    pack = assistant_chat.ask_context.build("hello", engine="local", model="granite3.3:2b", conversation_id=conversation_id)
    assert "CHAT_HISTORY_SENTINEL" not in pack


def test_forget_action_removes_saved_chats_and_turns_history_off(tmp_path, monkeypatch):
    _prepare(tmp_path, monkeypatch)
    conversation_id = "b" * 36
    assistant_chat._append_conversation(conversation_id, "Remember this", "Saved answer")
    result = assistant_chat.forget_conversations()
    assert result == {"forgotten": 1, "remember_previous_chats": False}
    assert vault.list_notes(".md", "conversations") == []
    assert assistant_chat.ask_context.remember_chats() is False


@pytest.mark.parametrize("engine", ["codex", "claude", "gemini", "openai", "anthropic", "local"])
def test_every_engine_adapter_receives_the_shared_pack(tmp_path, monkeypatch, engine):
    _prepare(tmp_path, monkeypatch)
    captured = []
    monkeypatch.setattr(assistant_chat.ask_context, "build", lambda *a, **k: "SHARED_PACK_SENTINEL")
    adapter = "_ask_api" if engine in {"openai", "anthropic"} else "_ask_cli" if engine in {"claude", "gemini"} else "_ask_local" if engine == "local" else "_ask_codex"
    if adapter == "_ask_api":
        monkeypatch.setattr(assistant_chat, adapter, lambda route, message, **kwargs: captured.append((route, message)) or {"reply": "ok", "automation": False})
    elif adapter == "_ask_cli":
        monkeypatch.setattr(assistant_chat, adapter, lambda route, message: captured.append((route, message)) or {"reply": "ok", "automation": False})
    else:
        monkeypatch.setattr(assistant_chat, adapter, lambda message: captured.append((engine, message)) or {"reply": "ok", "automation": False})
    monkeypatch.setattr(assistant_chat, "ask_route", lambda: (engine, "available"))
    _chat("Please use private-token-123")
    assert captured and captured[0][0] == engine
    assert "SHARED_PACK_SENTINEL" in captured[0][1]
    assert "private-token-123" not in captured[0][1]


def test_engine_settings_validate_and_report_unavailable_choice(tmp_path, monkeypatch):
    _prepare(tmp_path, monkeypatch)
    monkeypatch.setattr(assistant_chat, "available_engines", lambda: [{"id": "local", "label": "Ollama", "available": True, "reason": "Ollama is ready", "reason_code": "ready"}])
    saved = assistant_chat.save_ask_settings({"engine": "codex", "remember_previous_chats": True})
    assert saved["engine"] == "codex"
    assert saved["available"] is False
    assert "sign" in saved["reason"].lower()
    assert assistant_chat.get_ask_settings()["engine"] == "codex"


def test_cli_sign_in_discovery_uses_official_status_or_credential_presence(tmp_path, monkeypatch):
    monkeypatch.setattr(assistant_chat.shell_commands, "which", lambda name: f"/fake/{name}")
    gemini_home = tmp_path / "gemini-home"
    (gemini_home / ".gemini").mkdir(parents=True)
    (gemini_home / ".gemini" / "oauth_creds.json").write_text('{"access_token":"DO_NOT_RETURN_THIS"}', encoding="utf-8")
    monkeypatch.setattr(assistant_chat.Path, "home", staticmethod(lambda: gemini_home))
    assert assistant_chat._cli_available("gemini") == (True, "Gemini CLI is installed and has saved sign-in details.")
    monkeypatch.setattr(assistant_chat.subprocess, "run", lambda *_a, **_kw: type("Result", (), {"returncode": 0})())
    assert assistant_chat._cli_available("claude")[0] is True
    assert "DO_NOT_RETURN_THIS" not in str(assistant_chat._cli_available("gemini"))


def test_openai_api_adapter_uses_saved_secret_and_egress_without_network(tmp_path, monkeypatch):
    _prepare(tmp_path, monkeypatch)
    from contextlib import closing
    settings_path = tmp_path / "home" / "settings.json"
    settings_path.write_text(json.dumps({"openai_base_url": "https://api.example.test/v1", "openai_model": "fake",
                                        "openai_secret_name": "OPENAI_KEY", "openai_monthly_cap_usd": 1,
                                        "openai_input_usd_per_million": 1, "openai_output_usd_per_million": 3}), encoding="utf-8")
    monkeypatch.setenv("GLACIER_ALLOWED_HOSTS", "api.example.test")
    monkeypatch.setattr(assistant_chat.secrets_store, "_value", lambda name: "secret-value" if name == "OPENAI_KEY" else None)
    seen = {}
    class FakeResponse:
        def read(self):
            return json.dumps({"usage": {"prompt_tokens": 10, "completion_tokens": 5},
                               "choices": [{"message": {"content": json.dumps({"reply": "stand-in", "automation": False})}}]}).encode()
        def close(self):
            pass
    class FakeOpener:
        def open(self, request, timeout):
            seen["url"] = request.full_url
            seen["headers"] = dict(request.header_items())
            seen["body"] = request.data.decode()
            seen["timeout"] = timeout
            return closing(FakeResponse())
    monkeypatch.setattr(assistant_chat, "validate_url", lambda url, domains: seen.update({"validated": (url, domains)}))
    monkeypatch.setattr(assistant_chat, "pinned_opener", lambda domains: FakeOpener())
    result = assistant_chat._ask_api("openai", "shared context and question")
    assert result["reply"] == "stand-in"
    assert seen["validated"] == ("https://api.example.test/v1/chat/completions", {"api.example.test"})
    assert seen["headers"]["Authorization"] == "Bearer secret-value"
    assert "secret-value" not in seen["body"]
    assert assistant_chat.get_ask_settings()["openai_spend_usd"] == 0.000025


def test_api_engine_is_unavailable_until_host_is_allowlisted(tmp_path, monkeypatch):
    _prepare(tmp_path, monkeypatch)
    (tmp_path / "home" / "settings.json").write_text(json.dumps({"openai_base_url": "https://api.example.test/v1",
        "openai_model": "fake", "openai_secret_name": "OPENAI_KEY", "openai_monthly_cap_usd": 1,
        "openai_input_usd_per_million": 1, "openai_output_usd_per_million": 1}), encoding="utf-8")
    monkeypatch.setattr(assistant_chat.shell_commands, "which", lambda _name: None)
    monkeypatch.setattr(assistant_chat, "_ollama_answers", lambda: False)
    monkeypatch.setattr(assistant_chat.secrets_store, "names", lambda: ["OPENAI_KEY"])
    monkeypatch.delenv("GLACIER_ALLOWED_HOSTS", raising=False)
    engine = next(item for item in assistant_chat.available_engines() if item["id"] == "openai")
    assert engine["available"] is False and engine["reason_code"] == "host_not_allowed"
    monkeypatch.setenv("GLACIER_ALLOWED_HOSTS", "api.example.test")
    engine = next(item for item in assistant_chat.available_engines() if item["id"] == "openai")
    assert engine["available"] is True


@pytest.mark.parametrize("budget", ["missing", "reached"])
def test_api_call_is_blocked_without_monthly_budget_or_at_cap(tmp_path, monkeypatch, budget):
    _prepare(tmp_path, monkeypatch)
    settings = {"openai_base_url": "https://api.example.test/v1", "openai_model": "fake",
                "openai_secret_name": "OPENAI_KEY", "openai_input_usd_per_million": 1,
                "openai_output_usd_per_million": 1}
    if budget == "reached":
        settings["openai_monthly_cap_usd"] = 0.01
    (tmp_path / "home" / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
    if budget == "reached":
        month = assistant_chat.datetime.now(assistant_chat.timezone.utc).strftime("%Y-%m")
        (tmp_path / "home" / "ask_api_usage.json").write_text(json.dumps({month: {"openai": 0.01}}), encoding="utf-8")
    monkeypatch.setenv("GLACIER_ALLOWED_HOSTS", "api.example.test")
    monkeypatch.setattr(assistant_chat.secrets_store, "_value", lambda _name: "secret-value")
    monkeypatch.setattr(assistant_chat, "validate_url", lambda _url, _domains: None)
    monkeypatch.setattr(assistant_chat, "pinned_opener", lambda _domains: pytest.fail("API request must not be sent"))
    with pytest.raises(RuntimeError, match="monthly cap|monthly cap and token prices"):
        assistant_chat._ask_api("openai", "do not send")
