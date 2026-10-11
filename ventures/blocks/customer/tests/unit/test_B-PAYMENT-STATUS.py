from __future__ import annotations

import http.client
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit

from ventures.blocks import customer


class RecordedStripe(BaseHTTPRequestHandler):
    sessions: dict[str, dict] = {}
    next_id = 1
    posted_success_url = ""

    def _reply(self, status: int, value: dict) -> None:
        payload = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self) -> None:
        fields = parse_qs(self.rfile.read(int(self.headers["Content-Length"])).decode())
        if self.path != "/v1/checkout/sessions":
            self._reply(404, {})
            return
        type(self).posted_success_url = fields["success_url"][0]
        session_id = f"cs_test_status_{RecordedStripe.next_id}"
        RecordedStripe.next_id += 1
        RecordedStripe.sessions[session_id] = {
            "id": session_id,
            "status": "open",
            "payment_status": "unpaid",
            "livemode": False,
            "client_reference_id": fields.get("client_reference_id", [None])[0],
            "metadata": {"customer_id": fields.get("metadata[customer_id]", [None])[0]},
        }
        self._reply(200, {"id": session_id, "url": f"https://checkout.stripe.test/{session_id}"})

    def do_GET(self) -> None:
        session_id = self.path.removeprefix("/v1/checkout/sessions/")
        session = RecordedStripe.sessions.get(session_id)
        self._reply(200, session) if session else self._reply(404, {"error": {"message": "unknown session"}})

    def log_message(self, *_args) -> None:
        pass


def _get(port: int, path: str) -> tuple[int, str]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    try:
        connection.request("GET", path, headers={"Host": f"127.0.0.1:{port}"})
        response = connection.getresponse()
        return response.status, response.read().decode("utf-8", errors="replace")
    finally:
        connection.close()


def _return_path(tmp_path, customer_id: str, provider: HTTPServer, server: HTTPServer) -> tuple[str, str]:
    customer.configure_stripe_for_tests(f"http://127.0.0.1:{provider.server_port}")
    success_url = f"http://127.0.0.1:{server.server_port}/customer/success?session_id={{CHECKOUT_SESSION_ID}}"
    customer.checkout_link(
        "synthetic",
        secret_getter=lambda _name: "sk_test_recorded",
        plans={"synthetic": {"price_id": "price_test_fixture", "mode": "payment", "success_url": success_url}},
        customer_id=customer_id,
        db_path=tmp_path / "customers.db",
    )
    session_id = f"cs_test_status_{RecordedStripe.next_id - 1}"
    parsed = urlsplit(RecordedStripe.posted_success_url.replace("{CHECKOUT_SESSION_ID}", session_id))
    return parsed.path + "?" + parsed.query, f"cs_test_status_{RecordedStripe.next_id - 1}"


def _servers(tmp_path):
    RecordedStripe.sessions = {}
    RecordedStripe.next_id = 1
    RecordedStripe.posted_success_url = ""
    provider = HTTPServer(("127.0.0.1", 0), RecordedStripe)
    provider_thread = threading.Thread(target=provider.serve_forever, daemon=True)
    provider_thread.start()
    server = customer.create_signature_server(
        tmp_path, port=0, secret_getter=lambda _name: "sk_test_recorded"
    )
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    return provider, provider_thread, server, server_thread


def _stop(provider, provider_thread, server, server_thread):
    customer.configure_stripe_for_tests(None)
    server.shutdown()
    server_thread.join(timeout=2)
    server.server_close()
    provider.shutdown()
    provider_thread.join(timeout=2)
    provider.server_close()


def test_direct_success_visit_does_not_confirm_payment(tmp_path):
    provider, provider_thread, server, server_thread = _servers(tmp_path)
    try:
        status, page = _get(server.server_port, "/customer/success?session_id=cs_test_unknown")
        assert status == 403
        assert "Payment complete" not in page
        assert not RecordedStripe.sessions
        status, page = _get(server.server_port, "/customer/cancelled")
        assert status == 200
        assert "Checkout cancelled" in page
        assert "Payment complete" not in page
    finally:
        _stop(provider, provider_thread, server, server_thread)


def test_unpaid_checkout_is_pending_and_expired_checkout_is_not_complete(tmp_path):
    provider, provider_thread, server, server_thread = _servers(tmp_path)
    try:
        return_path, session_id = _return_path(tmp_path, "customer-17", provider, server)
        status, page = _get(server.server_port, return_path)
        assert status == 200
        assert "Payment pending verification" in page
        assert "Payment complete" not in page

        RecordedStripe.sessions[session_id].update(status="expired")
        # A new checkout gets a fresh one-time token for the expired-session case.
        return_path, session_id = _return_path(tmp_path, "customer-17", provider, server)
        RecordedStripe.sessions[session_id].update(status="expired")
        status, page = _get(server.server_port, return_path)
        assert status == 200
        assert "Checkout expired" in page
        assert "Payment complete" not in page
    finally:
        _stop(provider, provider_thread, server, server_thread)


def test_wrong_customer_checkout_remains_pending(tmp_path):
    provider, provider_thread, server, server_thread = _servers(tmp_path)
    try:
        return_path, session_id = _return_path(tmp_path, "customer-expected", provider, server)
        RecordedStripe.sessions[session_id].update(
            status="complete", payment_status="paid", client_reference_id="customer-other"
        )
        status, page = _get(server.server_port, return_path)
        assert status == 200
        assert "Payment pending verification" in page
        assert "Payment complete" not in page
    finally:
        _stop(provider, provider_thread, server, server_thread)


def test_only_paid_test_session_for_expected_customer_confirms(tmp_path):
    provider, provider_thread, server, server_thread = _servers(tmp_path)
    try:
        return_path, session_id = _return_path(tmp_path, "customer-expected", provider, server)
        RecordedStripe.sessions[session_id].update(status="complete", payment_status="paid")
        status, page = _get(server.server_port, return_path)
        assert status == 200
        assert "Payment complete" in page
        assert "Payment pending verification" not in page
    finally:
        _stop(provider, provider_thread, server, server_thread)
