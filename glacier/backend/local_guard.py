"""Browser request checks for the loopback engine."""

from urllib.parse import urlsplit
import os

import local_token

from starlette.responses import JSONResponse


BLOCKED = "This request came from another website and was blocked."
NOT_OURS = "This request isn't from your Glacier app."
OPEN_PATHS = {"/api/health"}
TAURI_ORIGINS = {"tauri://localhost", "http://tauri.localhost", "https://tauri.localhost"}
FORM_TYPES = {"application/x-www-form-urlencoded", "multipart/form-data", "text/plain"}
STATE_CHANGING = {"POST", "PUT", "PATCH", "DELETE"}


def _allowed_origin(origin: str, request) -> bool:
    if origin in TAURI_ORIGINS:
        return True
    try:
        parsed = urlsplit(origin)
        port = parsed.port
    except ValueError:
        return False
    if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1"}:
        return False
    host = request.headers.get("host", "").rsplit(":", 1)[0].strip("[]").lower()
    own_port = request.url.port
    if parsed.hostname.lower() == host and port == own_port:
        return True
    return os.environ.get("GLACIER_DEV") == "1" and port in {5173, 4173}


def _host_is_loopback(host_header: str) -> bool:
    try:
        parsed = urlsplit("//" + host_header)
        port = parsed.port  # Access validates that an optional port is numeric and in range.
        return (parsed.hostname in {"localhost", "127.0.0.1"} and parsed.username is None
                and parsed.password is None and parsed.path == "" and parsed.query == "" and parsed.fragment == ""
                and (port is None or 1 <= port <= 65535))
    except ValueError:
        return False


class LocalRequestGuard:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return
        headers = {key.decode("latin1").lower(): value.decode("latin1") for key, value in scope.get("headers", [])}
        host = headers.get("host", "")
        if not _host_is_loopback(host):
            await self._reject(scope, receive, send)
            return

        if scope["type"] == "websocket":
            origin = headers.get("origin")
            if origin and not _allowed_origin(origin, _RequestView(scope, headers)):
                await self._reject(scope, receive, send)
                return
            if not self._has_token(scope, headers):
                await self._unauthorized(scope, receive, send)
                return
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "").upper()
        if method in STATE_CHANGING:
            origin = headers.get("origin")
            fetch_site = headers.get("sec-fetch-site", "").lower()
            if (origin and not _allowed_origin(origin, _RequestView(scope, headers))) or (not origin and fetch_site == "cross-site"):
                await self._reject(scope, receive, send)
                return
            content_type = headers.get("content-type", "").split(";", 1)[0].strip().lower()
            if content_type in FORM_TYPES and scope.get("path") not in {"/api/files", "/api/imports"}:
                response = JSONResponse({"detail": "This form cannot be used for this request."}, status_code=415)
                await response(scope, receive, send)
                return
        if not self._has_token(scope, headers):
            await self._unauthorized(scope, receive, send)
            return
        await self.app(scope, receive, send)

    @staticmethod
    def _has_token(scope, headers) -> bool:
        """Install token required on /api (except the open health check and CORS preflight)."""
        path = scope.get("path", "")
        if not (path.startswith("/api") or path == "/a2a") or path in OPEN_PATHS or scope.get("method", "").upper() == "OPTIONS":
            return True
        query = scope.get("query_string", b"").decode("latin1") if scope["type"] == "websocket" else ""
        return local_token.matches(local_token.from_headers_or_query(headers, query))


    @staticmethod
    async def _unauthorized(scope, receive, send):
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008, "reason": NOT_OURS})
            return
        response = JSONResponse({"detail": NOT_OURS}, status_code=401)
        await response(scope, receive, send)

    @staticmethod
    async def _reject(scope, receive, send):
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return
        response = JSONResponse({"detail": BLOCKED}, status_code=403)
        await response(scope, receive, send)


class _RequestView:
    """Small URL view used without constructing a framework Request."""
    def __init__(self, scope, headers):
        self.scope = scope
        self.headers = headers

    @property
    def url(self):
        from starlette.datastructures import URL
        if self.scope["type"] == "websocket":
            server = self.scope.get("server")
            if server:
                scheme = "https" if self.scope.get("scheme") == "wss" else "http"
                return URL(scheme=scheme, hostname=server[0], port=server[1])
        from starlette.requests import Request
        return Request(self.scope).url
