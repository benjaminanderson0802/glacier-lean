"""Acceptance checks for read-only IMAP polling and exactly-once email starts."""
import json


def test_email_trigger_baselines_existing_mail_then_starts_each_new_message_once(tmp_path, monkeypatch):
    import runner
    import triggers

    env = {"id": "mail-watch", "enabled": True, "nodes": [
        {"id": "inbox", "type": "email_trigger", "config": {"host": "imap.example.test", "user": "team@example.test",
            "password": "{secret:MAIL_APP}", "folder": "INBOX", "search": "UNSEEN"}},
    ], "edges": []}
    messages = [{"message_id": "<old@example.test>", "subject": "Existing", "from": "one@example.test"}]
    starts = []
    monkeypatch.setattr(triggers.vault, "list_notes", lambda suffix, folder: ["environments/mail-watch.json"])
    monkeypatch.setattr(triggers.vault, "read_note", lambda path: json.dumps(env))
    monkeypatch.setattr(triggers.email_read, "run", lambda ctx: {"state": "done", "output": json.dumps(messages)})
    monkeypatch.setattr(runner, "start_run", lambda env_id, settings, run_id=None: starts.append((env_id, settings, run_id)) or run_id)

    assert triggers.scan_email_once(str(tmp_path)) == 0
    assert starts == []
    messages.append({"message_id": "<new@example.test>", "subject": "New", "from": "two@example.test"})
    assert triggers.scan_email_once(str(tmp_path)) == 1
    assert starts[0][0] == "mail-watch"
    assert starts[0][1]["_trigger"]["type"] == "email"
    assert starts[0][1]["_trigger"]["body"]["subject"] == "New"
    assert triggers.scan_email_once(str(tmp_path)) == 0
    assert len(starts) == 1
