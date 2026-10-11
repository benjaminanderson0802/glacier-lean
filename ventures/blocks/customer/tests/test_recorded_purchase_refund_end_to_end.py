"""Recorded provider responses: create checkout, complete test card purchase, refund."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

from ventures.blocks import customer


class RecordedStripe(BaseHTTPRequestHandler):
    sessions = {}
    next_id = 1

    def _reply(self, status, value):
        body = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        form = parse_qs(self.rfile.read(int(self.headers["Content-Length"])).decode())
        if self.path == "/v1/checkout/sessions":
            session_id = f"cs_test_{type(self).next_id}"
            type(self).next_id += 1
            type(self).sessions[session_id] = {"form": form, "status": "open", "payment_intent": None}
            self._reply(200, {"id": session_id, "url": f"https://checkout.stripe.test/{session_id}"})
        elif self.path == "/v1/refunds":
            payment_intent = form["payment_intent"][0]
            if not any(s["payment_intent"] == payment_intent and s["status"] == "complete"
                       for s in type(self).sessions.values()):
                self._reply(400, {"error": {"message": "No completed recorded purchase for payment intent"}})
                return
            self._reply(200, {"id": "re_test_recorded", "status": "succeeded", "payment_intent": payment_intent})
        else:
            self._reply(404, {"error": {"message": "not found"}})

    def do_GET(self):
        path = urlparse(self.path).path
        prefix = "/mock/purchase/"
        if not path.startswith(prefix):
            self._reply(404, {"error": {"message": "not found"}})
            return
        session_id = path[len(prefix):]
        session = type(self).sessions.get(session_id)
        if not session:
            self._reply(404, {"error": {"message": "unknown session"}})
            return
        session.update(status="complete", payment_intent="pi_test_recorded")
        self._reply(200, {"id": session_id, "status": "complete", "payment_status": "paid",
                          "payment_intent": session["payment_intent"]})

    def log_message(self, *_args):
        pass


def test_recorded_checkout_purchase_refund_and_signature_flow(tmp_path):
    RecordedStripe.sessions = {}
    RecordedStripe.next_id = 1
    server = HTTPServer(("127.0.0.1", 0), RecordedStripe)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{server.server_port}"
    customer.configure_stripe_for_tests(base)
    try:
        link = customer.checkout_link("batch", secret_getter=lambda _: "sk_test_recorded",
                                      plans={"batch": {"price_id": "price_test_batch", "mode": "payment"}},
                                      db_path=tmp_path / "customers.db")
        session_id = link.rsplit("/", 1)[-1]
        assert RecordedStripe.sessions[session_id]["status"] == "open"
        assert RecordedStripe.sessions[session_id]["form"]["mode"] == ["payment"]

        # The recorded checkout page accepts a test card and returns the paid session's PaymentIntent.
        with urlopen(base + "/mock/purchase/" + session_id) as response:
            purchase = json.loads(response.read())
        assert purchase["payment_status"] == "paid"
        refund = customer.refund(purchase["payment_intent"], approval_id="owner-approved-test-refund",
                                 secret_getter=lambda _: "sk_test_recorded", db_path=tmp_path / "customers.db")
        assert refund["status"] == "succeeded"

        source = tmp_path / "authorization.txt"
        source.write_text("Test authorization", encoding="utf-8")
        request = customer.request_signature(source, {"name": "Test Signer"}, data_dir=tmp_path / "customer-data")
        signed = customer.sign_document(request["id"], typed_name="Test Signer", consent=True,
                                        data_dir=tmp_path / "customer-data")
        assert open(signed["pdf_path"], "rb").read().startswith(b"%PDF-")
        audit = json.loads(open(signed["audit_path"], encoding="utf-8").read())
        assert audit["consent"] and audit["signed_pdf_sha256"]
    finally:
        customer.configure_stripe_for_tests(None)
        server.shutdown()
        worker.join(timeout=2)
        server.server_close()
