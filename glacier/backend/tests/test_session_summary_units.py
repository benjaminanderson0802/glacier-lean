"""Unit coverage for summary titles, independent of the bounded event preview."""
import json

import session_mirror


def test_original_title_survives_event_preview_limit(tmp_path):
    path = tmp_path / "long.jsonl"
    records = [
        {"type": "session_meta", "payload": {"id": "long"}},
        {"type": "event_msg", "payload": {"type": "user_message", "message": "<environment_context>injected</environment_context>"}},
        {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"text": "Find the missing invoices"}]}},
    ]
    records.extend({"type": "event_msg", "payload": {"type": "agent_message", "message": f"Step {i}"}}
                   for i in range(session_mirror.MAX_EVENTS + 1))
    path.write_text("".join(json.dumps(row) + "\n" for row in records))
    summary, events, _, _ = session_mirror._load_file(path, include_events=False)
    assert summary["title"] == "Find the missing invoices"
    assert summary["truncated"] is True
    assert events == []
    detail, events, version, truncated = session_mirror._load_file(path)
    assert detail["title"] == summary["title"]
    assert len(events) == session_mirror.MAX_EVENTS
    assert truncated and len(version) == 64


def test_summary_keeps_timestamp_extremes_and_refreshes_after_append(tmp_path):
    path = tmp_path / "times.jsonl"
    path.write_text(json.dumps({"type": "session_meta", "payload": {"id": "times"}}) + "\n")
    with path.open("a") as stream:
        for timestamp in ("2026-10-10T12:00:00Z", "2026-10-10T10:00:00Z", "2026-10-10T11:00:00Z"):
            stream.write(json.dumps({"type": "event_msg", "timestamp": timestamp,
                                     "payload": {"type": "agent_message", "message": "Working"}}) + "\n")
    summary = session_mirror._load_file(path, include_events=False)[0]
    assert summary["started"] == "2026-10-10T10:00:00+00:00"
    assert summary["updated"] == "2026-10-10T12:00:00+00:00"
    with path.open("a") as stream:
        stream.write(json.dumps({"type": "event_msg", "timestamp": "2026-10-10T13:00:00Z",
                                 "payload": {"type": "user_message", "message": "Show my invoices"}}) + "\n")
    summary = session_mirror._load_file(path, include_events=False)[0]
    assert summary["updated"] == "2026-10-10T13:00:00+00:00"
    assert summary["title"] == "Show my invoices"
