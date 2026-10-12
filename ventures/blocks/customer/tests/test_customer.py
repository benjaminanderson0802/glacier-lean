import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs

import pytest

from ventures.blocks import customer


class StripeRecorder(BaseHTTPRequestHandler):
    state = {"checkout": None, "refund": None}

    def do_POST(self):
        body = parse_qs(self.rfile.read(int(self.headers["Content-Length"])).decode())
        if self.path == "/v1/checkout/sessions":
            type(self).state["checkout"] = body
            result = {"id": "cs_test_recorded", "url": "https://checkout.stripe.test/cs_test_recorded"}
        elif self.path == "/v1/refunds":
            type(self).state["refund"] = body
            result = {"id": "re_test_recorded", "status": "succeeded", "payment_intent": body["payment_intent"][0]}
        else:
            self.send_error(404)
            return
        payload = json.dumps(result).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_args):
        pass


def _stripe_mock():
    server = HTTPServer(("127.0.0.1", 0), StripeRecorder)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def test_account_persists_in_local_sqlite(tmp_path):
    db = tmp_path / "customers.db"
    created = customer.create_customer({"name": "Acme Imports", "email": "billing@example.test"}, db_path=db)
    assert created["id"]
    assert customer.get_customer(created["id"], db_path=db)["email"] == "billing@example.test"


def test_missing_stripe_secret_has_actionable_message(monkeypatch):
    monkeypatch.setattr(customer, "_secret", lambda _name: None)
    with pytest.raises(customer.CustomerError, match="Add STRIPE_SECRET_KEY in Glacier Settings > Secrets"):
        customer.checkout_link("monthly", secret_getter=lambda _name: None)


def test_checkout_purchase_and_refund_use_test_mode_and_approval(tmp_path):
    server, thread = _stripe_mock()
    try:
        customer.configure_stripe_for_tests(f"http://127.0.0.1:{server.server_port}")
        db = tmp_path / "billing.db"
        link = customer.checkout_link(
            "monthly", secret_getter=lambda name: "sk_test_recorded" if name == "STRIPE_SECRET_KEY" else None,
            plans={"monthly": {"price_id": "price_test_monthly"}},
            db_path=db,
        )
        assert link == "https://checkout.stripe.test/cs_test_recorded"
        assert StripeRecorder.state["checkout"]["line_items[0][price]"] == ["price_test_monthly"]
        result = customer.refund("pi_test_recorded", approval_id="approval-42",
                                  secret_getter=lambda _name: "sk_test_recorded", db_path=db)
        assert result["status"] == "succeeded"
        assert StripeRecorder.state["refund"]["payment_intent"] == ["pi_test_recorded"]
        assert StripeRecorder.state["refund"]["metadata[approval_id]"] == ["approval-42"]
    finally:
        customer.configure_stripe_for_tests(None)
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_live_stripe_key_is_refused_by_test_helper(monkeypatch):
    with pytest.raises(customer.CustomerError, match="Stripe test-mode key"):
        customer.checkout_link("monthly", secret_getter=lambda _name: "sk_live_not_allowed")


def test_signature_request_creates_signed_pdf_and_audit_trail(tmp_path):
    source = tmp_path / "terms.txt"
    source.write_text("Service terms: sample", encoding="utf-8")
    request = customer.request_signature(source, {"name": "Ada Customer", "email": "ada@example.test"},
                                         data_dir=tmp_path / "customer-data")
    assert Path(request["page_path"]).is_file()
    signed = customer.sign_document(request["id"], typed_name="Ada Customer", consent=True,
                                    data_dir=tmp_path / "customer-data")
    pdf = Path(signed["pdf_path"]).read_bytes()
    assert pdf.startswith(b"%PDF-")
    assert b"Ada Customer" in pdf
    audit = json.loads(Path(signed["audit_path"]).read_text(encoding="utf-8"))
    assert audit["signer"] == "Ada Customer"
    assert audit["document_sha256"]
    assert audit["signed_pdf_sha256"]
    assert audit["consent"] is True


def test_status_page_is_static_and_escapes_customer_content(tmp_path):
    item = customer.create_customer({"name": "<script>alert(1)</script>", "email": "x@example.test"},
                                    db_path=tmp_path / "customer-data" / "customers.db")
    page = Path(customer.status_page(item["id"], data_dir=tmp_path / "customer-data"))
    html = page.read_text(encoding="utf-8")
    assert "&lt;script&gt;" in html
    assert "<script>alert(1)</script>" not in html


def test_imap_support_reads_mail_and_keeps_reply_as_unapproved_draft(tmp_path):
    class FakeImap:
        def login(self, *_args): pass
        def select(self, *_args, **_kwargs): return "OK", [b"1"]
        def search(self, *_args): return "OK", [b"1"]
        def fetch(self, *_args):
            return "OK", [(b"1 (RFC822)", b"From: help@example.test\r\nSubject: Question\r\n\r\nPlease help.")]
        def logout(self): pass

    inbox = customer.support_inbox(
        config={"host": "imap.example.test", "username": "support", "password_secret": "IMAP_PASSWORD"},
        secret_getter=lambda name: "mail-secret" if name == "IMAP_PASSWORD" else None,
        imap_factory=lambda _host: FakeImap(), db_path=tmp_path / "customers.db",
    )
    assert inbox[0]["subject"] == "Question"
    draft = customer.draft_reply(inbox[0]["id"], "We received your message.", db_path=tmp_path / "customers.db")
    assert draft["status"] == "pending_approval"
    with pytest.raises(customer.CustomerError, match="approval"):
        customer.send_reply(draft["id"], approval_id="", db_path=tmp_path / "customers.db")
