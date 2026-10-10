"""Acceptance tests for generated product context and screen awareness."""
import json

import vault
from routes import assistant_chat
import glacier_context


def _prepare(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("GLACIER_HOME", str(home))
    vault.init(str(tmp_path / "vault"))
    monkeypatch.setattr(assistant_chat, "ask_route", lambda: ("codex", "available"))
    monkeypatch.setattr(assistant_chat, "_ask", lambda prompt, route: _capture(prompt))
    monkeypatch.setattr(assistant_chat.ask_context, "_system_state", lambda *a, **k: "Current system state: tests")


_prompts = []


def _capture(prompt):
    _prompts.append(prompt)
    return {"reply": "I can help you build an interview.", "automation": False}


def test_generated_context_has_current_mission_screens_api_and_ui_rules(tmp_path, monkeypatch):
    _prepare(tmp_path, monkeypatch)
    vault.write_note("notes/about-me.md", "The owner prefers concise, practical help.", agent="owner")
    full = glacier_context.build(engine="codex", model="gpt-6")
    compact = glacier_context.build(engine="local", model="granite3.3:2b")
    assert "hand goals and recurring work" in full
    assert "concise, practical help" in full
    assert all(value in full for value in ("Home", "Build", "Automations", "Memory", "Settings"))
    assert "glacier/web/src/App.tsx" in full
    assert "glacier/web/src/ui/wallQuad.ts" in full
    assert "theme lint" in full.lower()
    assert "/api/assistant/chat" in full
    assert len(compact) < len(full)
    assert "Glacier" in compact


def test_context_cache_refreshes_when_repo_source_changes(monkeypatch, tmp_path):
    _prepare(tmp_path, monkeypatch)
    repo = tmp_path / "repo"
    repo.mkdir()
    northstar = repo / "NORTHSTAR.yaml"
    northstar.write_text("mission: >\n  First mission from the generated pack.\n", encoding="utf-8")
    monkeypatch.setattr(glacier_context, "ROOT", repo)
    glacier_context.clear_cache()
    first = glacier_context.build(engine="codex", model="gpt-6")
    northstar.write_text("mission: >\n  Updated mission from the generated pack.\n", encoding="utf-8")
    second = glacier_context.build(engine="codex", model="gpt-6")
    assert "First mission" in first
    assert "Updated mission" in second
    assert glacier_context.cache_misses() == 2


def test_screen_and_focus_are_validated_and_included_in_prompt(tmp_path, monkeypatch):
    _prepare(tmp_path, monkeypatch)
    _prompts.clear()
    events = assistant_chat.chat(assistant_chat.ChatRequest(message="Help me", screen="build", focus="interview"))
    body = "".join(__import__("asyncio").run(_collect(events.body_iterator)))
    assert "TEXT_MESSAGE_CONTENT" in body
    assert "You're on build" in _prompts[-1]
    assert "interview" in _prompts[-1]


def test_ui_change_chat_emits_review_only_tool_and_rejects_without_writing(tmp_path, monkeypatch):
    _prepare(tmp_path, monkeypatch)
    diff = ("--- a/glacier/web/src/App.tsx\n+++ b/glacier/web/src/App.tsx\n"
            "@@ -1 +1 @@\n-old\n+new\n")
    monkeypatch.setattr(assistant_chat, "_ui_change_draft", lambda *args: {
        "diff": diff, "explanation": "Make the welcome easier to scan.",
        "related_spec": "glacier/web/e2e/shell.spec.mjs"})
    events = assistant_chat.chat(assistant_chat.ChatRequest(message="Change Glacier's UI to simplify the welcome screen"))
    body = "".join(__import__("asyncio").run(_collect(events.body_iterator)))
    assert '"propose_ui_change"' in body
    assert "preparing a review-only UI change" in body
    proposal = next(value for value in assistant_chat._proposals.values() if value.get("kind") == "ui_change")
    assert not (assistant_chat.ui_change.ROOT / "glacier/web/src/App.tsx").read_text().startswith("new")
    result = assistant_chat.apply_proposal(proposal["id"], assistant_chat.ApplyRequest(approve=False))
    assert result == {"discarded": True}
    assert not (assistant_chat.ui_change.ROOT / "glacier/web/src/App.tsx").read_text().startswith("new")


def test_ui_change_chat_without_source_returns_setup_message(tmp_path, monkeypatch):
    _prepare(tmp_path, monkeypatch)
    monkeypatch.setattr(assistant_chat.ui_change, "ROOT", tmp_path / "missing-source")
    events = assistant_chat.chat(assistant_chat.ChatRequest(message="Change Glacier's UI to simplify the home screen"))
    body = "".join(__import__("asyncio").run(_collect(events.body_iterator)))
    assert "UI changes need the Glacier source folder" in body
    assert "glacier_source_dir" in body
    assert '"type": "RUN_FINISHED"' in body
    assert '"type": "RUN_ERROR"' not in body


def test_ui_proposal_apply_dispatches_only_after_owner_approval(tmp_path, monkeypatch):
    _prepare(tmp_path, monkeypatch)
    proposal = assistant_chat.ui_change.propose(
        "--- a/glacier/web/src/App.tsx\n+++ b/glacier/web/src/App.tsx\n@@ -1 +1 @@\n-old\n+new\n",
        "A clearer welcome.", "glacier/web/e2e/shell.spec.mjs")
    proposal["conversation_id"] = "c" * 36
    assistant_chat._proposals[proposal["id"]] = proposal
    seen = []
    result = {"applied": True, "branch": "assistant/ui-change/test", "passed": True, "checks": []}
    monkeypatch.setattr(assistant_chat.ui_change, "apply", lambda proposal_id, item: seen.append(proposal_id) or result)
    monkeypatch.setattr(assistant_chat, "_append_conversation", lambda *args: None)
    monkeypatch.setattr(assistant_chat.audit_log, "record", lambda *args, **kwargs: None)
    assert assistant_chat.apply_proposal(proposal["id"], assistant_chat.ApplyRequest(approve=False)) == {"discarded": True}
    assert seen == []
    assistant_chat._proposals[proposal["id"]] = proposal
    assert assistant_chat.apply_proposal(proposal["id"], assistant_chat.ApplyRequest(approve=True)) == result
    assert seen == [proposal["id"]]


async def _collect(iterator):
    return [chunk async for chunk in iterator]
