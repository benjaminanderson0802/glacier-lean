"""Per-step web egress checks for fetched pages."""

from __future__ import annotations

import ipaddress
import http.client
import socket
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPHandler, HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener


class EgressError(PermissionError):
    pass


class _RejectModelRedirects(HTTPRedirectHandler):
    """Keep model calls on the exact address selected by the owner."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HTTPError(req.full_url, code, "Model server redirected the request.", headers, fp)




def _validate_model_url(url: str) -> None:
    try:
        parsed = urlsplit(url)
        _ = parsed.port
    except ValueError:
        raise ValueError("Use an http or https model address without sign-in details.") from None
    if (parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname
            or parsed.username is not None or parsed.password is not None):
        raise ValueError("Use an http or https model address without sign-in details.")


def model_opener():
    """Build an opener that bypasses system proxies and refuses model redirects."""
    return build_opener(ProxyHandler({}), _RejectModelRedirects())


def open_model_request(request: Request | str, timeout: float = 30):
    """Send one request to its configured model URL, without proxy or redirect hops."""
    url = request.full_url if isinstance(request, Request) else request
    _validate_model_url(url)
    opener = model_opener()
    return opener.open(request, timeout=timeout)


def allowed_domains(value: str | list[str] | None) -> set[str]:
    if isinstance(value, list):
        parts = value
    else:
        parts = str(value or "").split(",")
    return {part.strip().lower().rstrip(".") for part in parts if part.strip()}


def _host_allowed(host: str, domains: set[str]) -> bool:
    return any(host == domain or host.endswith("." + domain) for domain in domains)


def _resolve_public(host: str) -> list[str]:
    try:
        ipaddress.ip_address(host)
        resolved = [host]
    except ValueError:
        try:
            resolved = list({item[4][0] for item in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)})
        except OSError as exc:
            raise EgressError("Glacier could not find this site's address.") from exc
    if not resolved:
        raise EgressError("Glacier could not find this site's address.")
    for address in resolved:
        ip = ipaddress.ip_address(address.split("%", 1)[0])
        if not ip.is_global:
            raise EgressError("This site points to a private or reserved network address, so Glacier stopped.")
    return resolved


def validate_url(url: str, domains: set[str], *, allow_loopback: bool = False) -> str:
    if "{secret:" in url.lower():
        raise EgressError("Remove the secret placeholder from this web address first.")
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        # Accessing port validates malformed port syntax before any network request.
        _ = parsed.port
    except ValueError as exc:
        raise EgressError("Enter a valid http or https web address.") from exc
    if parsed.scheme.lower() not in {"http", "https"} or not host:
        raise EgressError("Use an http or https web address.")
    if parsed.username is not None or parsed.password is not None:
        raise EgressError("Remove the sign-in details from this web address first.")
    if not domains or not _host_allowed(host, domains):
        raise EgressError("Add this site to the step's allowed sites first.")
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if allow_loopback and literal is not None and literal.is_loopback:
        return host
    _resolve_public(host)
    return host


def _pinned_socket(host: str, port: int, timeout, source_address, *, allow_loopback=False):
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    address = host if allow_loopback and literal is not None and literal.is_loopback else _resolve_public(host)[0]
    # Create the socket using the pinned numeric address directly. Using
    # create_connection here would resolve the host again on some platforms.
    family = socket.AF_INET6 if ":" in address else socket.AF_INET
    sock = socket.socket(family, socket.SOCK_STREAM)
    try:
        if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
            sock.settimeout(timeout)
        if source_address:
            sock.bind(source_address)
        sockaddr = (address, port, 0, 0) if family == socket.AF_INET6 else (address, port)
        sock.connect(sockaddr)
        return sock
    except BaseException:
        sock.close()
        raise


class _PinnedHTTPConnection(http.client.HTTPConnection):
    allow_loopback = False

    def connect(self):
        self.sock = _pinned_socket(self.host, self.port, self.timeout, self.source_address,
                                   allow_loopback=self.allow_loopback)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    allow_loopback = False

    def connect(self):
        sock = _pinned_socket(self.host, self.port, self.timeout, self.source_address,
                              allow_loopback=self.allow_loopback)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


class _PinnedHTTPHandler(HTTPHandler):
    allow_loopback = False

    def http_open(self, req):
        connection = type("PinnedHTTPConnection", (_PinnedHTTPConnection,),
                          {"allow_loopback": self.allow_loopback})
        return self.do_open(connection, req)


class _PinnedHTTPSHandler(HTTPSHandler):
    allow_loopback = False

    def https_open(self, req):
        connection = type("PinnedHTTPSConnection", (_PinnedHTTPSConnection,),
                          {"allow_loopback": self.allow_loopback})
        return self.do_open(connection, req, context=self._context)


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, new_url):
        return None


def pinned_opener(domains: set[str], *, allow_loopback: bool = False):
    """Build a proxy-free urllib opener that checks and pins each destination."""
    return build_opener(ProxyHandler({}),
                        type("PinnedHTTPHandler", (_PinnedHTTPHandler,), {"allow_loopback": allow_loopback})(),
                        type("PinnedHTTPSHandler", (_PinnedHTTPSHandler,), {"allow_loopback": allow_loopback})(),
                        _NoRedirectHandler())


def open_pinned(request, domains: set[str], timeout: float = 10, *, allow_loopback: bool = False):
    """Open a request, validating every redirect before its pinned connection."""
    opener = pinned_opener(domains, allow_loopback=allow_loopback)
    current = request
    for redirect_count in range(4):
        validate_url(current.full_url, domains, allow_loopback=allow_loopback)
        try:
            response = opener.open(current, timeout=timeout)
        except HTTPError as exc:
            if exc.code not in {301, 302, 303, 307, 308}:
                raise
            response = exc
        if response.status not in {301, 302, 303, 307, 308}:
            return response
        location = response.headers.get("Location")
        response.close()
        if not location:
            raise EgressError("Glacier could not reach this page. Check the address and try again.")
        if redirect_count == 3:
            raise EgressError("This page redirected too many times.")
        target = urljoin(current.full_url, location)
        target_host = (urlsplit(target).hostname or "").lower().rstrip(".")
        try:
            parsed = urlsplit(target)
            host = (parsed.hostname or "").lower().rstrip(".")
            if not any(host == domain or host.endswith("." + domain) for domain in domains):
                raise EgressError(f"Glacier is not allowed to reach {target_host}. Add it to the allowed sites first.")
            validate_url(target, domains, allow_loopback=allow_loopback)
        except EgressError as exc:
            raise exc
        from urllib.request import Request
        current = Request(target, headers=dict(current.headers), method=current.get_method())
    raise EgressError("This page redirected too many times.")
