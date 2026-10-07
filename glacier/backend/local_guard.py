"""Browser request checks for the loopback engine."""

from urllib.parse import urlsplit

from starlette.responses import JSONResponse


BLOCKED = "This request came from another website and was blocked."
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
    return port in {5173, 4173}


def _host_is_loopback(host_header: str) -> bool:
    try:
        parsed = urlsplit("//" + host_header)
        return parsed.hostname in {"localhost", "127.0.0.1"} and parsed.username is None and parsed.password is None
    except ValueError:
        return False


class LocalRequestGuard:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {key.decode("latin1").lower(): value.decode("latin1") for key, value in scope.get("headers", [])}
        host = headers.get("host", "")
        if not _host_is_loopback(host):
            response = JSONResponse({"detail": BLOCKED}, status_code=403)
            await response(scope, receive, send)
            return

        method = scope.get("method", "").upper()
        if method in STATE_CHANGING:
            origin = headers.get("origin")
            fetch_site = headers.get("sec-fetch-site", "").lower()
            if (origin and not _allowed_origin(origin, _RequestView(scope, headers))) or (not origin and fetch_site == "cross-site"):
                response = JSONResponse({"detail": BLOCKED}, status_code=403)
                await response(scope, receive, send)
                return
            content_type = headers.get("content-type", "").split(";", 1)[0].strip().lower()
            if content_type in FORM_TYPES and scope.get("path") != "/api/files":
                response = JSONResponse({"detail": "This form cannot be used for this request."}, status_code=415)
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


class _RequestView:
    """Small URL view used without constructing a framework Request."""
    def __init__(self, scope, headers):
        from starlette.requests import Request
        self._request = Request(scope)
        self.headers = headers

    @property
    def url(self):
        return self._request.url
