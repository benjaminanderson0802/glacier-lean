import os
import sys
from urllib.request import ProxyHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import nodes.read_document as read_document


def test_document_reader_disables_environment_proxies(monkeypatch):
    monkeypatch.setattr(read_document, "_allowed_hosts", lambda: {"127.0.0.1"})
    seen = []

    class Response:
        headers = {"Content-Type": "text/plain"}

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def read(self, _limit):
            return b"ok"

    class Opener:
        def open(self, _request, timeout):
            return Response()

    def build_opener(*handlers):
        seen.extend(handlers)
        return Opener()

    monkeypatch.setattr(read_document, "build_opener", build_opener)
    read_document._read_url("http://127.0.0.1/document")

    assert any(isinstance(handler, ProxyHandler) and handler.proxies == {} for handler in seen)
