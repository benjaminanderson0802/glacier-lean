import json

import pytest

from glacier.importers import chatgpt, claude, common


def test_chatgpt_uses_visible_current_node_chain_and_skips_other_messages():
    conversation = {
        "id": "chat-1",
        "title": "Branches",
        "create_time": 0,
        "current_node": "a2",
        "mapping": {
            "a2": {"parent": "u2", "message": {"author": {"role": "assistant"}, "content": {"parts": ["Answer"]}}},
            "branch": {"parent": "u1", "message": {"author": {"role": "assistant"}, "content": {"parts": ["Not visible"]}}},
            "u2": {"parent": "u1", "message": {"author": {"role": "user"}, "content": {"parts": ["Question"]}}},
            "u1": {"parent": "root", "message": {"author": {"role": "user"}, "content": {"parts": ["First"]}}},
            "root": {"parent": None, "message": {"author": {"role": "system"}, "content": {"parts": ["Hidden"]}}},
            "tool": {"parent": None, "message": {"author": {"role": "browser"}, "content": {"parts": ["Tool output"]}}},
            "empty": {"parent": None, "message": {"author": {"role": "assistant"}, "content": {"parts": [""]}}},
        },
    }
    [note] = chatgpt.parse(json.dumps([conversation]))
    assert note.source_id == "chat-1"
    assert "## You\n\nFirst\n\n## You\n\nQuestion\n\n## ChatGPT\n\nAnswer" in note.body
    assert "Not visible" not in note.body
    assert "Hidden" not in note.body
    assert "Tool output" not in note.body
    assert "message_count: 3" in note.body


def test_paths_slug_collisions_and_empty_title():
    chats = [
        {"id": "1", "title": "Hello, World!", "create_time": 0, "mapping": {}},
        {"id": "2", "title": "Hello, World!", "create_time": 0, "mapping": {}},
        {"id": "3", "title": "", "create_time": 0, "mapping": {}},
    ]
    notes = chatgpt.parse(json.dumps(chats))
    assert [note.path for note in notes] == [
        "imports/chatgpt/1970-01-01-hello-world.md",
        "imports/chatgpt/1970-01-01-hello-world-2.md",
        "imports/chatgpt/1970-01-01-untitled.md",
    ]


def test_claude_parses_text_and_content_messages_in_order():
    chats = [{
        "uuid": "claude-1", "name": "A chat", "created_at": "2024-03-04T12:30:00Z",
        "chat_messages": [
            {"sender": "human", "text": "Hi"},
            {"sender": "assistant", "content": [{"text": "Hello"}]},
            {"sender": "human", "text": ""},
        ],
    }]
    [note] = claude.parse(json.dumps(chats))
    assert note.path == "imports/claude/2024-03-04-a-chat.md"
    assert "## You\n\nHi\n\n## Claude\n\nHello" in note.body
    assert "message_count: 2" in note.body


def test_dedupe_drops_known_body_hashes():
    [note] = claude.parse(json.dumps([{"uuid": "x", "name": "Notes", "created_at": "2024-01-01", "chat_messages": []}]))
    assert common.dedupe([note], set()) == [note]
    assert common.dedupe([note], {note.content_hash}) == []
    assert common.dedupe([note, note], set()) == [note]


def test_malformed_json_has_friendly_value_error():
    with pytest.raises(ValueError, match="valid JSON"):
        chatgpt.parse("{oops")
