"""Search a configured SearXNG server and return a small plain-text result list."""

from __future__ import annotations

import http.client
import ipaddress
import json
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPHandler, HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener

import egress
from egress import EgressError

_MAX_DOWNLOAD = 2 * 1024 * 1024
_TIMEOUT = 10
_USER_AGENT = "Glacier (local automation)"
_INSTALL_URL = "https://docs.searxng.org/admin/installation.html"
_NO_SERVER = ("Add a SearXNG search server to this step. SearXNG is free and open source. "
              f"You can run it on your computer or choose a public server you trust. Install guide: {_INSTALL_URL}")


def _failed(message: str) -> dict:
    return {"state": "failed", "output": message, "exit_code": 1,
            "usage": {"model": "searxng", "route": "user-configured search server",
                      "tokens_in": 0, "tokens_out": 0, "cost_usd": 0}}


def _resolve(host: str, allow_private: bool) -> list[str]:
    """Resolve once and pin the socket to checked addresses, with opt-in for private hosts."""
    try:
        ipaddress.ip_address(host)
        addresses = [host]
    except ValueError:
        try:
            addresses = list({item[4][0] for item in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)})
        except OSError as exc:
            raise EgressError("Glacier could not find this search server's address.") from exc
    if not addresses:
        raise EgressError("Glacier could not find this search server's address.")
    for address in addresses:
        ip = ipaddress.ip_address(address.split("%", 1)[0])
        if not ip.is_global and not allow_private:
            raise EgressError("This search server points to a private or reserved network address. Turn on the network option only if you trust this server.")
    return addresses


def _validate_url(url: str, allow_private: bool) -> tuple[str, list[str]]:
    if "{secret:" in url.lower():
        raise EgressError("Remove the secret placeholder from this search server address first.")
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        port = parsed.port
    except ValueError as exc:
        raise EgressError("Enter a valid http or https search server address.") from exc
    if parsed.scheme.lower() not in {"http", "https"} or not host:
        raise EgressError("Use an http or https search server address.")
    if parsed.username is not None or parsed.password is not None:
        raise EgressError("Remove the sign-in details from this search server address first.")
    if parsed.fragment:
        raise EgressError("Enter the search server address without a fragment.")
    # Standard port validation happens above; force default ports into the checked target.
    addresses = _resolve(host, allow_private)
    return host, addresses


def _pinned_socket(host: str, port: int, timeout, source_address, addresses: list[str]):
    # Use the addresses checked for this request; no global opener or cache state.
    last_error = None
    for address in addresses:
        try:
            return socket.create_connection((address, port), timeout, source_address)
        except OSError as exc:
            last_error = exc
    raise last_error or OSError("Could not connect to the search server.")


class _PinnedHTTPConnection(http.client.HTTPConnection):
    pass


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    pass


def _handlers(allow_private: bool, original_host: str, original_addresses: list[str]):
    checked_addresses = {original_host: original_addresses}

    def validate_target(url: str) -> str:
        host, addresses = _validate_url(url, allow_private if host_matches(url, original_host) else False)
        checked_addresses[host] = addresses
        return host

    def host_matches(url: str, expected: str) -> bool:
        try:
            return (urlsplit(url).hostname or "").lower().rstrip(".") == expected
        except ValueError:
            return False

    class PinnedHTTPConnection(_PinnedHTTPConnection):
        def connect(self):
            addresses = checked_addresses.get(self.host.lower().rstrip("."), [])
            if not addresses:
                raise EgressError("This search server address was not checked.")
            self.sock = _pinned_socket(self.host, self.port, self.timeout, self.source_address, addresses)

    class PinnedHTTPSConnection(_PinnedHTTPSConnection):
        def connect(self):
            addresses = checked_addresses.get(self.host.lower().rstrip("."), [])
            if not addresses:
                raise EgressError("This search server address was not checked.")
            sock = _pinned_socket(self.host, self.port, self.timeout, self.source_address, addresses)
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)

    class PinnedHTTPHandler(HTTPHandler):
        def http_open(self, req):
            return self.do_open(PinnedHTTPConnection, req)

    class PinnedHTTPSHandler(HTTPSHandler):
        def https_open(self, req):
            return self.do_open(PinnedHTTPSConnection, req, context=self._context)

    class CheckedRedirectHandler(HTTPRedirectHandler):
        def __init__(self):
            super().__init__()
            self.count = 0
            self.policy_error = None

        def redirect_request(self, req, fp, code, msg, headers, newurl):
            self.count += 1
            if self.count > 3:
                raise EgressError("The search server redirected too many times.")
            try:
                validate_target(urljoin(req.full_url, newurl))
            except EgressError as exc:
                self.policy_error = exc
                return None
            return super().redirect_request(req, fp, code, msg, headers, newurl)

        def http_error_302(self, req, fp, code, msg, headers):
            return super().http_error_302(req, fp, code, msg, headers)

        http_error_301 = http_error_302
        http_error_303 = http_error_302
        http_error_307 = http_error_302
        http_error_308 = http_error_302

    return [ProxyHandler({}), PinnedHTTPHandler(), PinnedHTTPSHandler(), CheckedRedirectHandler()]


def _search(server: str, query: str, count: int, allow_private: bool) -> list[dict]:
    if not server:
        raise EgressError(_NO_SERVER)
    if "{secret:" in query.lower():
        raise EgressError("Remove the secret placeholder from the search text first.")
    if not query.strip():
        raise EgressError("Add search words to this step first.")
    server_host, server_addresses = _validate_url(server, allow_private)
    parsed = urlsplit(server)
    path = parsed.path.rstrip("/") + "/search"
    search_url = urlunsplit((parsed.scheme, parsed.netloc, path, urlencode({"q": query, "format": "json"}), ""))
    search_host, search_addresses = _validate_url(search_url, allow_private)
    if search_host != server_host:
        raise EgressError("Use the configured search server address without changing its host.")
    handlers = _handlers(allow_private, server_host, search_addresses or server_addresses)
    redirect_handler = handlers[-1]
    opener = build_opener(*handlers)
    request = Request(search_url, headers={"User-Agent": _USER_AGENT, "Accept": "application/json"})
    try:
        response = opener.open(request, timeout=_TIMEOUT)
    except HTTPError as exc:
        response = exc
    except (URLError, TimeoutError, OSError, EgressError) as exc:
        if redirect_handler.policy_error:
            raise redirect_handler.policy_error
        if isinstance(getattr(exc, "reason", None), EgressError):
            raise exc.reason
        if isinstance(getattr(exc, "fp", None), EgressError):
            raise exc.fp
        if isinstance(exc, EgressError):
            raise
        raise EgressError("Glacier could not reach this search server. Check its address and try again.") from exc
    if redirect_handler.policy_error:
        raise redirect_handler.policy_error
    with response:
        final_host, _ = _validate_url(response.geturl(), allow_private if response.geturl() == search_url else False)
        if final_host != server_host:
            raise EgressError("The search server redirected to a different address, so Glacier stopped.")
        if response.status >= 400:
            raise EgressError(f"The search server answered with an error ({response.status}).")
        data = response.read(_MAX_DOWNLOAD + 1)
        if len(data) > _MAX_DOWNLOAD:
            raise EgressError("The search response is too large (the limit is 2 MB).")
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EgressError("Glacier could not read the search server's response. Check that SearXNG JSON results are enabled.") from exc
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        raise EgressError("Glacier could not read the search server's response. Check that SearXNG JSON results are enabled.")
    return results[:count]


def run(ctx: dict) -> dict:
    config = ctx.get("config") or {}
    server = str(config.get("search_server", "")).strip()
    query = str(config.get("query", "")).strip()
    try:
        count = int(config.get("result_count", 5))
    except (TypeError, ValueError):
        count = 5
    count = max(1, min(20, count))
    allow_private = bool(config.get("allow_private_network", False))
    try:
        results = _search(server, query, count, allow_private)
    except EgressError as exc:
        return _failed(str(exc))
    except Exception:
        return _failed("Glacier could not read the search server's response. Check that SearXNG JSON results are enabled.")
    lines = []
    for item in results:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "(No title)").replace("\r", " ").replace("\n", " ")
        link = str(item.get("url") or "").replace("\r", " ").replace("\n", " ")
        snippet = str(item.get("content") or item.get("snippet") or "").replace("\r", " ").replace("\n", " ")
        lines.append(f"{title}\n{link}\n{snippet}")
    output = "\n\n".join(lines) if lines else "No search results were returned."
    return {"state": "done", "output": output, "exit_code": 0,
            "usage": {"model": "searxng", "route": "user-configured search server",
                      "tokens_in": 0, "tokens_out": 0, "cost_usd": 0}}


NODE = {
    "catalog": {
        "type": "web_search", "label": "Search the web",
        "description": "Search a SearXNG server you choose and pass a few results to the next step.",
        "fields": [
            {"key": "query", "label": "Search words", "placeholder": "What would you like to find?", "default": ""},
            {"key": "search_server", "label": "Search server", "placeholder": "http://localhost:8888", "default": ""},
            {"key": "result_count", "label": "Number of results", "placeholder": "5", "default": 5},
            {"key": "allow_private_network", "label": "The search server runs on this computer or my network", "default": False},
        ],
        "branches": None, "worker": True,
    },
    "run": run,
}
