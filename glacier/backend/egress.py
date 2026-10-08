"""Per-step web egress checks for fetched pages."""

from __future__ import annotations

import ipaddress
import socket
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


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


def validate_url(url: str, domains: set[str]) -> str:
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
    _resolve_public(host)
    return host
