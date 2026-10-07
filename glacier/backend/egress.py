"""Per-step web egress checks for fetched pages."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit


class EgressError(PermissionError):
    pass


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
