import http.server
import socketserver
import threading

import pytest

import egress
from nodes.read_document import _read_url


class Handler(http.server.BaseHTTPRequestHandler):
    body = b"<html><body>pinned content</body></html>"
    redirect = None

    def do_GET(self):
        if self.redirect:
            self.send_response(302)
            self.send_header("Location", self.redirect)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *_args):
        pass


@pytest.fixture
def local_server():
    servers = []

    def serve(*, redirect=None):
        handler = type("TestHandler", (Handler,), {"redirect": redirect})
        server = socketserver.TCPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        servers.append((server, thread))
        return server.server_address[1]

    serve.servers = servers
    yield serve
    for server, thread in servers:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_refuses_listed_host_resolving_to_loopback(monkeypatch):
    monkeypatch.setenv("GLACIER_ALLOWED_HOSTS", "listed.test")
    monkeypatch.setattr(egress.socket, "getaddrinfo", lambda *_a, **_kw: [
        (2, 1, 6, "", ("127.0.0.1", 0)),
    ])

    with pytest.raises(PermissionError, match="private or reserved"):
        _read_url("http://listed.test/")


def test_dns_change_cannot_redirect_connection(monkeypatch, local_server):
    port = local_server()
    monkeypatch.setenv("GLACIER_ALLOWED_HOSTS", "pinned.test")
    resolutions = []

    def resolve(host):
        resolutions.append(host)
        return ["127.0.0.1"]

    monkeypatch.setattr(egress, "_resolve_public", resolve)
    data, _content_type = _read_url(f"http://pinned.test:{port}/")

    assert b"pinned content" in data
    assert resolutions and set(resolutions) == {"pinned.test"}


def test_redirect_to_private_address_is_refused(monkeypatch, local_server):
    port = local_server()
    # The server port is appended after startup so the redirect stays local.
    redirect_host = "private.test"
    for server, _thread in local_server.servers:
        if server.server_address[1] == port:
            server.RequestHandlerClass.redirect = f"http://{redirect_host}:{port}/"
    monkeypatch.setenv("GLACIER_ALLOWED_HOSTS", "listed.test, private.test")

    def resolve(host):
        if host == redirect_host:
            raise egress.EgressError("This site points to a private or reserved network address, so Glacier stopped.")
        return ["127.0.0.1"]

    monkeypatch.setattr(egress, "_resolve_public", resolve)

    with pytest.raises(PermissionError, match="private or reserved"):
        _read_url(f"http://listed.test:{port}/")


def test_public_looking_fake_works_through_pinned_path(monkeypatch, local_server):
    port = local_server()
    monkeypatch.setenv("GLACIER_ALLOWED_HOSTS", "reader.test")
    connections = []
    original_connect = egress.socket.socket.connect

    def record(sock, address):
        connections.append(address)
        return original_connect(sock, address)

    monkeypatch.setattr(egress, "_resolve_public", lambda _host: ["127.0.0.1"])
    monkeypatch.setattr(egress.socket.socket, "connect", record)
    data, content_type = _read_url(f"http://reader.test:{port}/")

    assert b"pinned content" in data
    assert content_type == "text/html"
    assert connections == [("127.0.0.1", port)]
