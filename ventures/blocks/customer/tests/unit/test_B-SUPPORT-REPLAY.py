from __future__ import annotations

import json
import sqlite3
import threading

import pytest

from ventures.blocks import customer


def make_draft(db_path):
    class FakeImap:
        def login(self, *_args):
            pass

        def select(self, *_args, **_kwargs):
            return "OK", [b"1"]

        def search(self, *_args):
            return "OK", [b"1"]

        def fetch(self, *_args):
            raw = (b"Message-ID: <help-1@example.test>\r\n"
                   b"From: help@example.test\r\nSubject: Help\r\n\r\nQuestion")
            return "OK", [(b"1 (RFC822)", raw)]

        def logout(self):
            pass

    message = customer.support_inbox(
        config={"host": "imap.example.test", "username": "support", "password_secret": "IMAP_PASSWORD"},
        secret_getter=lambda _name: "local-test-secret", imap_factory=lambda _host: FakeImap(), db_path=db_path,
    )[0]
    return customer.draft_reply(message["id"], "We can help.", db_path=db_path)


def audit_events(db_path, draft_id):
    with customer._database(db_path) as db:
        return [dict(row) for row in db.execute(
            "SELECT event, approval_id, details_json FROM audit_events WHERE subject_id=? ORDER BY id",
            (draft_id,),
        )]


def test_concurrent_send_claims_draft_once_and_records_delivery_identity(tmp_path):
    db_path = tmp_path / "customers.db"
    draft = make_draft(db_path)
    sender_entered = threading.Event()
    release_sender = threading.Event()
    attempts = []
    outcomes = []

    def sender(recipient, body, *, message_id):
        attempts.append((recipient, body, message_id))
        sender_entered.set()
        assert release_sender.wait(timeout=5)

    def first_send():
        try:
            customer.send_reply(draft["id"], approval_id="approval-once", smtp_sender=sender, db_path=db_path)
            outcomes.append("sent")
        except Exception as exc:  # recorded for the assertion on the caller thread
            outcomes.append(str(exc))

    first = threading.Thread(target=first_send)
    first.start()
    assert sender_entered.wait(timeout=5), "first send should reach the fake transport"
    with pytest.raises(customer.CustomerError, match="uncertain|no longer pending"):
        customer.send_reply(draft["id"], approval_id="approval-once", smtp_sender=sender, db_path=db_path)
    release_sender.set()
    first.join(timeout=5)

    assert not first.is_alive()
    assert outcomes == ["sent"]
    assert len(attempts) == 1
    assert attempts[0][:2] == ("help@example.test", "We can help.")
    assert attempts[0][2].startswith("<") and attempts[0][2].endswith("@glacier.local>")
    stored = customer.list_support_drafts(db_path=db_path)[0]
    assert stored["status"] == "sent"
    assert stored["outbound_message_id"] == attempts[0][2]
    events = audit_events(db_path, draft["id"])
    assert [event["event"] for event in events] == [
        "support_reply_drafted", "support_reply_claimed", "support_reply_sent",
    ]


def test_accepted_then_timeout_is_uncertain_until_reconciled(tmp_path):
    db_path = tmp_path / "customers.db"
    draft = make_draft(db_path)
    accepted = []

    def accepted_then_timeout(recipient, body, *, message_id):
        accepted.append((recipient, body, message_id))
        raise TimeoutError("fake SMTP accepted the message but lost its response")

    with pytest.raises(TimeoutError):
        customer.send_reply(draft["id"], approval_id="approval-first", smtp_sender=accepted_then_timeout,
                            db_path=db_path)

    uncertain = customer.list_support_drafts(db_path=db_path)[0]
    assert uncertain["status"] == "uncertain"
    assert uncertain["outbound_message_id"] == accepted[0][2]
    events = audit_events(db_path, draft["id"])
    assert [event["event"] for event in events] == [
        "support_reply_drafted", "support_reply_claimed", "support_reply_uncertain",
    ]
    assert json.loads(events[-1]["details_json"]) == {
        "outbound_message_id": accepted[0][2], "error_type": "TimeoutError", "status": "uncertain",
    }

    with pytest.raises(customer.CustomerError, match="uncertain"):
        customer.send_reply(draft["id"], approval_id="approval-retry", smtp_sender=accepted_then_timeout,
                            db_path=db_path)
    assert len(accepted) == 1

    customer.reconcile_reply(draft["id"], delivered=False, reconciliation_id="local-mailbox-check-1",
                             db_path=db_path)
    assert customer.list_support_drafts(db_path=db_path)[0]["status"] == "pending_approval"

    def accepted_successfully(recipient, body, *, message_id):
        accepted.append((recipient, body, message_id))

    customer.send_reply(draft["id"], approval_id="approval-after-reconciliation",
                        smtp_sender=accepted_successfully, db_path=db_path)
    assert len(accepted) == 2
    assert accepted[1][2] == accepted[0][2]
    assert customer.list_support_drafts(db_path=db_path)[0]["status"] == "sent"
    assert audit_events(db_path, draft["id"])[-3]["event"] == "support_reply_reconciled"


def test_confirmed_delivery_reconciliation_records_sent_without_retry(tmp_path):
    db_path = tmp_path / "customers.db"
    draft = make_draft(db_path)

    def accepted_then_timeout(_recipient, _body):
        raise TimeoutError("response lost after acceptance")

    with pytest.raises(TimeoutError):
        customer.send_reply(draft["id"], approval_id="approval-first", smtp_sender=accepted_then_timeout,
                            db_path=db_path)
    customer.reconcile_reply(draft["id"], delivered=True, reconciliation_id="local-mailbox-check-2",
                             db_path=db_path)

    assert customer.list_support_drafts(db_path=db_path)[0]["status"] == "sent"
    events = audit_events(db_path, draft["id"])
    assert [event["event"] for event in events][-2:] == [
        "support_reply_reconciled", "support_reply_sent",
    ]
    with pytest.raises(customer.CustomerError, match="no longer pending"):
        customer.send_reply(draft["id"], approval_id="approval-retry", smtp_sender=accepted_then_timeout,
                            db_path=db_path)


def test_existing_customer_database_gains_outbound_message_identity_column(tmp_path):
    db_path = tmp_path / "customers.db"
    with sqlite3.connect(db_path) as db:
        db.execute("CREATE TABLE support_drafts (id TEXT PRIMARY KEY, message_id TEXT NOT NULL, body TEXT NOT NULL, "
                   "status TEXT NOT NULL, created_at TEXT NOT NULL, approved_at TEXT, approval_id TEXT)")
        db.execute("INSERT INTO support_drafts VALUES ('draft-old', 'message-old', 'reply', "
                   "'pending_approval', '2026-10-11T00:00:00+00:00', NULL, NULL)")

    with customer._database(db_path) as db:
        columns = {row["name"] for row in db.execute("PRAGMA table_info(support_drafts)")}
        draft = db.execute("SELECT * FROM support_drafts WHERE id='draft-old'").fetchone()

    assert "outbound_message_id" in columns
    assert draft["status"] == "pending_approval"
    assert draft["outbound_message_id"] is None
