"""Acceptance tests for model requests staying on their configured address."""
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request

import pytest

import egress


class _Server:
    def __init__(self, *, redirect=None):
        self.requests = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                owner.requests.append(self.path)
                if redirect:
                    self.send_response(302)
                    self.send_header("Location", redirect)
                    self.end_headers()
                    return
                body = b"ok"
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def close(self):
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()


def test_model_request_works_locally_and_ignores_proxy_environment(monkeypatch):
    server = _Server()
    try:
        monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
        monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:1")
        request = Request(server.url + "/model", data=b"{}")
        with egress.open_model_request(request, timeout=2) as response:
            assert response.read() == b"ok"
        assert server.requests == ["/model"]
    finally:
        server.close()


def test_model_request_refuses_redirect_with_plain_error():
    server = _Server(redirect="http://example.invalid/secret")
    try:
        request = Request(server.url + "/model", data=b"{}")
        with pytest.raises(HTTPError) as caught:
            egress.open_model_request(request, timeout=2)
        assert str(caught.value) == "HTTP Error 302: Model server redirected the request."
        assert server.requests == ["/model"]
    finally:
        server.close()


@pytest.mark.parametrize("url", ["ftp://example.com/model", "http://user:pass@example.com/model"])
def test_model_request_rejects_non_http_or_credentials(url):
    with pytest.raises(ValueError, match="Use an http or https model address without sign-in details."):
        egress.open_model_request(Request(url), timeout=1)
