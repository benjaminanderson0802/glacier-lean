import asyncio

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from bounded_body import read_bounded_body


def _request(body=b"", headers=()):
    messages = [{"type": "http.request", "body": body, "more_body": False}]

    async def receive():
        return messages.pop(0)

    scope = {"type": "http", "method": "POST", "path": "/", "headers": list(headers),
             "query_string": b"", "server": ("test", 80), "client": ("test", 1),
             "scheme": "http", "http_version": "1.1"}
    return Request(scope, receive)


def test_shared_body_limiter_accepts_exact_limit_and_preserves_body():
    request = _request(b"1234", [(b"content-length", b"4")])
    asyncio.run(read_bounded_body(request, 4, "Too large"))
    assert request._body == b"1234"


@pytest.mark.parametrize("incoming", [
    _request(b"", [(b"content-length", b"5")]),
    _request(b"12345"),
])
def test_shared_body_limiter_rejects_declared_and_chunked_over_limit(incoming):
    with pytest.raises(HTTPException) as error:
        asyncio.run(read_bounded_body(incoming, 4, "Route-specific message"))
    assert error.value.status_code == 413
    assert error.value.detail == "Route-specific message"
