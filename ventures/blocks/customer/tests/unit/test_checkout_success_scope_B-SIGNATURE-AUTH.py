from __future__ import annotations

import http.client
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit

import pytest

from ventures.blocks import customer


class RecordedCheckout(BaseHTTPRequestHandler):
    fields = None

    def do_POST(self):
        type(self).fields = parse_qs(self.rfile.read(int(self.headers["Content-Length"])).decode())
        payload = json.dumps({"id": "cs_test_signature_auth", "url": "https://checkout.example.test/session"}).encode()
        self.send_response(200)
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


def test_checkout_return_is_scoped_to_session_and_one_time(tmp_path):
    recorded = HTTPServer(("127.0.0.1", 0), RecordedCheckout)
    stripe_thread = threading.Thread(target=recorded.serve_forever, daemon=True)
    stripe_thread.start()
    server = customer.create_signature_server(tmp_path, port=0)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    customer.configure_stripe_for_tests(f"http://127.0.0.1:{recorded.server_port}")
    try:
        port = server.server_address[1]
        success_url = f"http://127.0.0.1:{port}/customer/success?session_id={{CHECKOUT_SESSION_ID}}"
        customer.checkout_link(
            "synthetic",
            secret_getter=lambda _name: "sk_test_fixture",
            plans={"synthetic": {"price_id": "price_test_fixture", "success_url": success_url}},
            db_path=tmp_path / "customers.db",
        )

        submitted_url = RecordedCheckout.fields["success_url"][0]
        assert "_glacier_return=" in submitted_url
        authorized_url = submitted_url.replace("{CHECKOUT_SESSION_ID}", "cs_test_signature_auth")
        parsed = urlsplit(authorized_url)
        authorized_path = parsed.path + "?" + parsed.query
        wrong_session = authorized_path.replace("cs_test_signature_auth", "cs_test_other")

        assert _get(port, "/customer/success")[0] == 403
        assert _get(port, wrong_session)[0] == 403
        status, page = _get(port, authorized_path)
        assert status == 200
        assert "verify your customer status" in page
        assert "Payment complete" not in page
        assert _get(port, authorized_path)[0] == 403
    finally:
        customer.configure_stripe_for_tests(None)
        server.shutdown()
        server_thread.join(timeout=2)
        server.server_close()
        recorded.shutdown()
        stripe_thread.join(timeout=2)
        recorded.server_close()


def test_signature_server_refuses_non_loopback_binding(tmp_path):
    with pytest.raises(customer.CustomerError, match="loopback address"):
        customer.create_signature_server(tmp_path, host="0.0.0.0", port=0)
