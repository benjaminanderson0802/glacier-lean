from __future__ import annotations

import http.client
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit

from ventures.blocks import customer


class RecordedProvider(BaseHTTPRequestHandler):
    created_ids: list[str] = []
    checkout_fields: dict[str, dict[str, list[str]]] = {}
    sessions: dict[str, dict[str, object]] = {}

    def do_POST(self):
        fields = parse_qs(self.rfile.read(int(self.headers["Content-Length"])).decode())
        session_id = f"cs_test_recorded_{len(type(self).created_ids) + 1}"
        type(self).created_ids.append(session_id)
        type(self).checkout_fields[session_id] = fields
        self._json({"id": session_id, "url": "https://checkout.example.test/recorded"})

    def do_GET(self):
        session_id = urlsplit(self.path).path.rsplit("/", 1)[-1]
        session = type(self).sessions.get(session_id)
        if session is None:
            self._json({"error": {"message": "unknown recorded checkout"}}, status=404)
            return
        self._json(session)

    def _json(self, value: dict[str, object], status: int = 200):
        payload = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_args):
        pass


def _get(port: int, path: str) -> tuple[int, str]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    try:
        connection.request("GET", path, headers={"Host": f"127.0.0.1:{port}"})
        response = connection.getresponse()
        return response.status, response.read().decode("utf-8", errors="replace")
    finally:
        connection.close()


def _path(url: str, session_id: str | None = None) -> str:
    if session_id is not None:
        url = url.replace("{CHECKOUT_SESSION_ID}", session_id)
    parsed = urlsplit(url)
    return parsed.path + (f"?{parsed.query}" if parsed.query else "")


def test_success_return_requires_one_time_verified_test_payment(tmp_path):
    RecordedProvider.created_ids = []
    RecordedProvider.checkout_fields = {}
    RecordedProvider.sessions = {}

    provider = HTTPServer(("127.0.0.1", 0), RecordedProvider)
    provider_thread = threading.Thread(target=provider.serve_forever, daemon=True)
    provider_thread.start()
    server = customer.create_signature_server(
        tmp_path,
        port=0,
        secret_getter=lambda _name: "sk_test_recorded_fixture",
    )
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    customer.configure_stripe_for_tests(f"http://127.0.0.1:{provider.server_port}")

    expected_customer = "cus_expected_recorded"

    def create_checkout() -> tuple[str, str, str]:
        session_id = f"cs_test_recorded_{len(RecordedProvider.created_ids) + 1}"
        port = server.server_address[1]
        success_url = f"http://127.0.0.1:{port}/customer/success?session_id={{CHECKOUT_SESSION_ID}}"
        customer.checkout_link(
            "synthetic",
            customer_id=expected_customer,
            secret_getter=lambda _name: "sk_test_recorded_fixture",
            plans={"synthetic": {"price_id": "price_test_recorded", "success_url": success_url}},
            db_path=tmp_path / "customers.db",
        )
        fields = RecordedProvider.checkout_fields[session_id]
        assert fields.get("metadata[customer_id]") == [expected_customer]
        return session_id, fields["success_url"][0], fields["cancel_url"][0]

    def set_provider_session(
        requested_id: str,
        *,
        returned_id: str | None = None,
        status: str = "complete",
        payment_status: str = "paid",
        customer_id: str | None = None,
        livemode: bool = False,
    ) -> None:
        fields = RecordedProvider.checkout_fields[requested_id]
        recorded_customer_id = fields["metadata[customer_id]"][0]
        associated_customer_id = customer_id or recorded_customer_id
        RecordedProvider.sessions[requested_id] = {
            "id": returned_id or requested_id,
            "object": "checkout.session",
            "status": status,
            "payment_status": payment_status,
            "livemode": livemode,
            "customer": associated_customer_id,
            "client_reference_id": recorded_customer_id,
            "metadata": {"customer_id": associated_customer_id},
        }

    try:
        port = server.server_address[1]

        # A public success URL by itself is not proof of payment.
        status, page = _get(port, "/customer/success")
        assert status == 403
        assert "payment complete" not in page.lower()

        # Canceled, unpaid, expired, and wrong-customer returns remain distinct.
        unpaid_id, unpaid_success, cancel_url = create_checkout()
        set_provider_session(unpaid_id, payment_status="unpaid")
        canceled_status, canceled_page = _get(port, _path(cancel_url))
        assert canceled_status == 200
        assert "cancel" in canceled_page.lower()
        assert "payment complete" not in canceled_page.lower()

        status, page = _get(port, _path(unpaid_success, unpaid_id))
        assert status == 200
        assert "pending verification" in page.lower()
        assert "payment complete" not in page.lower()

        expired_id, expired_success, _ = create_checkout()
        set_provider_session(expired_id, status="expired", payment_status="unpaid")
        status, page = _get(port, _path(expired_success, expired_id))
        assert status == 200
        assert "expired" in page.lower()
        assert "cancel" not in page.lower()
        assert "payment complete" not in page.lower()

        wrong_customer_id, wrong_customer_success, _ = create_checkout()
        set_provider_session(wrong_customer_id, customer_id="cus_someone_else")
        status, page = _get(port, _path(wrong_customer_success, wrong_customer_id))
        assert status == 200
        assert "pending verification" in page.lower()
        assert "payment complete" not in page.lower()

        wrong_checkout_id, wrong_checkout_success, _ = create_checkout()
        set_provider_session(wrong_checkout_id, returned_id="cs_test_different_checkout")
        status, page = _get(port, _path(wrong_checkout_success, wrong_checkout_id))
        assert status == 200
        assert "payment complete" not in page.lower()

        live_id, live_success, _ = create_checkout()
        set_provider_session(live_id, livemode=True)
        status, page = _get(port, _path(live_success, live_id))
        assert status == 200
        assert "payment complete" not in page.lower()

        # Only the exact, complete, paid, test-mode checkout for this customer completes.
        paid_id, paid_success, _ = create_checkout()
        set_provider_session(paid_id)
        success_path = _path(paid_success, paid_id)
        status, page = _get(port, success_path)
        assert status == 200
        assert "payment complete" in page.lower()
        assert _get(port, success_path)[0] == 403
    finally:
        customer.configure_stripe_for_tests(None)
        server.shutdown()
        server_thread.join(timeout=2)
        server.server_close()
        provider.shutdown()
        provider_thread.join(timeout=2)
        provider.server_close()
