"""Acceptance checks for local email drafts, approval-gated SMTP, and read-only IMAP search."""
import json
import sys
from email.message import EmailMessage
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nodes.email_send import NODE as SEND_NODE  # noqa: E402
from nodes.email_read import NODE as READ_NODE  # noqa: E402


def test_email_nodes_are_in_the_runner_catalog(server):
    catalog = {item["type"]: item for item in server.get("/api/node-types")}
    assert {"email_send", "email_read", "email_trigger"} <= catalog.keys()
    assert "draft_only" in {field["key"] for field in catalog["email_send"]["fields"]}


def context(tmp_path, config, previous=None, approved=False):
    return {"config": config, "home": str(tmp_path / "home"), "workspace": str(tmp_path / "workspace"),
            "prev": previous, "approved_by_human": approved}


def test_email_draft_is_saved_locally_without_contacting_smtp(tmp_path, monkeypatch):
    import nodes.email_send as email_send
    monkeypatch.setattr(email_send.secrets_store, "resolve", lambda value: value)
    monkeypatch.setattr(email_send.store, "get_run", lambda run_id: None)
    monkeypatch.setattr(email_send.audit_log, "record", lambda *args, **kwargs: None)
    monkeypatch.setattr(email_send.smtplib, "SMTP", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("draft connected to SMTP")))
    config = {"host": "smtp.example.test", "from": "team@example.test", "to": "ada@example.test",
              "subject": "Welcome", "body": "Hello Ada", "draft_only": "Yes"}
    result = SEND_NODE["run"](context(tmp_path, config))
    assert result["state"] == "done"
    draft = Path(context(tmp_path, config)["workspace"]) / result["output"]
    assert draft.is_file()
    assert "Subject: Welcome" in draft.read_text(encoding="utf-8")


def test_sending_email_requires_an_approval_result_and_uses_saved_secret(tmp_path, monkeypatch):
    import nodes.email_send as email_send
    sent = []

    class FakeSMTP:
        def __init__(self, host, port, timeout): sent.append(("connect", host, port, timeout))
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def ehlo(self): sent.append(("ehlo",))
        def starttls(self, context): sent.append(("tls",))
        def login(self, user, password): sent.append(("login", user, password))
        def send_message(self, message): sent.append(("send", message["To"], message["Subject"]))

    monkeypatch.setattr(email_send.secrets_store, "resolve", lambda value: value.replace("{secret:MAIL_APP}", "app-password"))
    monkeypatch.setattr(email_send.secrets_store, "redact", lambda value: value.replace("app-password", "[secret MAIL_APP]"))
    monkeypatch.setattr(email_send.store, "get_run", lambda run_id: None)
    monkeypatch.setattr(email_send.audit_log, "record", lambda *args, **kwargs: None)
    monkeypatch.setattr(email_send.smtplib, "SMTP", FakeSMTP)
    config = {"host": "smtp.example.test", "port": "587", "user": "team@example.test", "password": "{secret:MAIL_APP}",
              "from": "team@example.test", "to": "ada@example.test", "subject": "Welcome", "body": "Hello Ada",
              "draft_only": "No"}
    blocked = SEND_NODE["run"](context(tmp_path, config, {"output": "approved"}, approved=False))
    assert blocked["state"] == "failed"
    assert sent == []
    result = SEND_NODE["run"](context(tmp_path, config, {"output": "approved"}, approved=True))
    assert result["state"] == "done"
    assert ("login", "team@example.test", "app-password") in sent
    assert ("send", "ada@example.test", "Welcome") in sent
    assert "app-password" not in result["output"]


def test_imap_search_returns_message_summaries_without_marking_them_read(tmp_path, monkeypatch):
    import nodes.email_read as email_read
    message = EmailMessage()
    message["Message-ID"] = "<one@example.test>"
    message["From"] = "Ada <ada@example.test>"
    message["To"] = "team@example.test"
    message["Subject"] = "A sample"
    message["Date"] = "Mon, 01 Jan 2024 00:00:00 +0000"
    message.set_content("Hello Glacier")
    calls = []

    class FakeIMAP:
        def __init__(self, host, port, ssl_context, timeout=None): calls.append(("connect", host, port))
        def login(self, user, password): calls.append(("login", user, password))
        def select(self, folder, readonly=False): calls.append(("select", folder, readonly)); return "OK", [b"1"]
        def search(self, charset, query): calls.append(("search", query)); return "OK", [b"1"]
        def fetch(self, msg_id, request): calls.append(("fetch", msg_id, request)); return "OK", [(b"1 (RFC822)", message.as_bytes())]
        def logout(self): calls.append(("logout",))

    monkeypatch.setattr(email_read.imaplib, "IMAP4_SSL", FakeIMAP)
    monkeypatch.setattr(email_read.secrets_store, "resolve", lambda value: value.replace("{secret:MAIL_APP}", "app-password"))
    monkeypatch.setattr(email_read.store, "get_run", lambda run_id: None)
    monkeypatch.setattr(email_read.audit_log, "record", lambda *args, **kwargs: None)
    result = READ_NODE["run"](context(tmp_path, {"host": "imap.example.test", "user": "team@example.test",
                                                    "password": "{secret:MAIL_APP}", "search": "UNSEEN", "limit": "10"}))
    assert result["state"] == "done"
    assert json.loads(result["output"])[0]["subject"] == "A sample"
    assert ("select", "INBOX", True) in calls
    assert "STORE" not in {call[0] for call in calls}
