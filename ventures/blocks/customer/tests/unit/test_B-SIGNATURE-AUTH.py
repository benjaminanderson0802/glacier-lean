"""Black-box acceptance cases for B-SIGNATURE-AUTH.

These tests use only the public customer-layer calls and HTTP requests against
the resulting local server. All document data is synthetic and temporary.
"""

from __future__ import annotations

import hashlib
import http.client
import re
import threading
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

from ventures.blocks.customer import create_signature_server, request_signature


@contextmanager
def signature_server():
    with TemporaryDirectory() as data_dir:
        doc_path = Path(data_dir) / "synthetic-authorization.txt"
        doc_bytes = b"Synthetic authorization text for signature acceptance.\n"
        doc_path.write_bytes(doc_bytes)
        request = request_signature(
            doc_path,
            {"name": "Synthetic Signer", "email": "signer@example.test"},
            data_dir=data_dir,
        )
        server = create_signature_server(data_dir, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            host, port = server.server_address[:2]
            # request_signature currently returns its configured default URL;
            # route that same capability URL to the test server's ephemeral port.
            parts = urlsplit(request["url"])
            page_path = parts.path
            origin = f"http://{host}:{port}"
            yield data_dir, doc_path, doc_bytes, server, host, port, origin, page_path
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


def exchange(host, port, method, path, *, headers=None, body=None):
    connection = http.client.HTTPConnection(host, port, timeout=3)
    try:
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        return response.status, response.read().decode("utf-8", errors="replace")
    finally:
        connection.close()


def form_action(review_html):
    match = re.search(r'<form\b[^>]*\baction="([^"]+)"', review_html)
    assert match, "review page should expose the signing form action"
    return urlsplit(match.group(1)).path


def encoded_signature(signer="Synthetic Signer"):
    from urllib.parse import urlencode

    return urlencode({"typed_name": signer, "consent": "yes"})


def test_unauthenticated_customer_success_request_is_rejected():
    with signature_server() as (_, _, _, _, host, port, _, _):
        status, _ = exchange(host, port, "GET", "/customer/success")

    assert status in {401, 403}, "unauthenticated customer success access must be rejected"


def test_forged_host_cannot_fetch_signature_review():
    with signature_server() as (_, _, _, _, host, port, _, page_path):
        status, _ = exchange(host, port, "GET", page_path, headers={"Host": "attacker.invalid"})

    assert status in {400, 403}, "signature review must reject a forged Host header"


def test_forged_origin_cannot_submit_signature():
    with signature_server() as (_, _, _, _, host, port, origin, page_path):
        status, review = exchange(host, port, "GET", page_path, headers={"Host": f"{host}:{port}"})
        assert status == 200
        action = form_action(review)
        status, _ = exchange(
            host,
            port,
            "POST",
            action,
            headers={
                "Host": f"{host}:{port}",
                "Origin": "http://attacker.invalid",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            body=encoded_signature(),
        )

    assert status in {400, 403}, "signature POST must reject an untrusted Origin"


def test_same_origin_browser_flow_reviews_and_signs_once():
    with signature_server() as (
        data_dir,
        doc_path,
        doc_bytes,
        _,
        host,
        port,
        origin,
        page_path,
    ):
        headers = {"Host": f"{host}:{port}"}
        status, review = exchange(host, port, "GET", page_path, headers=headers)
        assert status == 200
        assert doc_path.name in review
        assert hashlib.sha256(doc_bytes).hexdigest() in review

        action = form_action(review)
        browser_headers = {
            **headers,
            "Origin": origin,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        status, signed = exchange(
            host,
            port,
            "POST",
            action,
            headers=browser_headers,
            body=encoded_signature(),
        )
        assert status == 200
        assert "Document signed" in signed
        assert "-signed.pdf" in signed
        signed_files_after_first_submit = list(Path(data_dir).rglob("*-signed.pdf"))

        replay_status, replay = exchange(
            host,
            port,
            "POST",
            action,
            headers=browser_headers,
            body=encoded_signature(),
        )
        signed_files_after_replay = list(Path(data_dir).rglob("*-signed.pdf"))

    assert replay_status in {400, 403, 409}, "a completed signature request must not be replayable"
    assert "already been completed" in replay
    assert len(signed_files_after_first_submit) == 1
    assert signed_files_after_replay == signed_files_after_first_submit


def test_signature_server_default_bind_is_loopback():
    with signature_server() as (_, _, _, server, *_):
        bound_host = server.server_address[0]

    assert bound_host == "127.0.0.1", "default signature server binding must remain local-only"
