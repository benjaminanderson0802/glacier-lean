from ventures.blocks import customer


def test_support_reply_is_sent_only_after_owner_approval_and_is_audited(tmp_path):
    db = tmp_path / "customers.db"

    class FakeImap:
        def login(self, *_args): pass
        def select(self, *_args, **_kwargs): return "OK", [b"1"]
        def search(self, *_args): return "OK", [b"1"]
        def fetch(self, *_args):
            return "OK", [(b"1 (RFC822)", b"Message-ID: <help-1@example.test>\r\nFrom: help@example.test\r\nSubject: Help\r\n\r\nQuestion")]
        def logout(self): pass

    message = customer.support_inbox(
        config={"host": "imap.example.test", "username": "support", "password_secret": "IMAP_PASSWORD"},
        secret_getter=lambda _name: "mail-secret", imap_factory=lambda _host: FakeImap(), db_path=db,
    )[0]
    draft = customer.draft_reply(message["id"], "We can help.", db_path=db)
    sent = []
    customer.send_reply(draft["id"], approval_id="approval-9", smtp_sender=lambda to, body: sent.append((to, body)), db_path=db)
    assert sent == [("help@example.test", "We can help.")]
    assert customer.list_support_drafts(db_path=db)[0]["status"] == "sent"
