"""Call one allow-listed web API with pinned outbound connections."""

from __future__ import annotations

import http.client
import ipaddress
import json
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPHandler, HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener

import egress
import secrets_store
from egress import EgressError, allowed_domains

_MAX_DOWNLOAD = 1024 * 1024
_MAX_CHARS = 20_000
_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


def _failed(message: str) -> dict:
    return {"state": "failed", "output": secrets_store.redact(message), "exit_code": 1,
            "usage": {"model": "http", "route": "user-configured API", "tokens_in": 0, "tokens_out": 0, "cost_usd": 0}}


def _allow_private(value) -> bool:
    return str(value or "No").strip().lower() in {"yes", "true", "1", "on"}


def _resolve(host: str, allow_private: bool) -> list[str]:
    try:
        addresses = [host] if _is_ip(host) else list({item[4][0] for item in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)})
    except OSError as exc:
        raise EgressError("Glacier could not find this site's address.") from exc
    if not addresses:
        raise EgressError("Glacier could not find this site's address.")
    for address in addresses:
        if not ipaddress.ip_address(address.split("%", 1)[0]).is_global and not allow_private:
            raise EgressError("This site points to a private or reserved network address. Turn on the network option only if you trust this API.")
    return addresses


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _validate_url(url: str, domains: set[str], allow_private: bool) -> tuple[str, list[str]]:
    if "{secret:" in url.lower():
        raise EgressError("Remove the secret placeholder from this web address first.")
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        _ = parsed.port
    except ValueError:
        raise EgressError("Enter a valid http or https web address.") from None
    if parsed.scheme.lower() not in {"http", "https"} or not host:
        raise EgressError("Use an http or https web address.")
    if parsed.username is not None or parsed.password is not None or parsed.fragment:
        raise EgressError("Remove sign-in details and fragments from this web address.")
    if not domains or not egress._host_allowed(host, domains):
        raise EgressError("Add this site to the step's allowed sites first.")
    return host, _resolve(host, allow_private)


def _pinned_socket(host: str, port: int, timeout, source_address, checked: dict[str, list[str]]):
    addresses = checked.get(host.lower().rstrip("."))
    if not addresses:
        raise EgressError("This API address was not checked.")
    last_error = None
    for address in addresses:
        try:
            return socket.create_connection((address, port), timeout, source_address)
        except OSError as exc:
            last_error = exc
    raise last_error or OSError("Could not connect to the API.")


def _open(url: str, method: str, headers: dict[str, str], body: bytes | None,
          domains: set[str], allow_private: bool, timeout: float):
    host, addresses = _validate_url(url, domains, allow_private)
    checked = {host: addresses}

    class PinnedHTTPConnection(http.client.HTTPConnection):
        def connect(self):
            self.sock = _pinned_socket(self.host, self.port, self.timeout, self.source_address, checked)

    class PinnedHTTPSConnection(http.client.HTTPSConnection):
        def connect(self):
            sock = _pinned_socket(self.host, self.port, self.timeout, self.source_address, checked)
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)

    class PinnedHTTPHandler(HTTPHandler):
        def http_open(self, req):
            return self.do_open(PinnedHTTPConnection, req)

    class PinnedHTTPSHandler(HTTPSHandler):
        def https_open(self, req):
            return self.do_open(PinnedHTTPSConnection, req, context=self._context)

    class CheckedRedirectHandler(HTTPRedirectHandler):
        count = 0
        policy_error = None

        def redirect_request(self, req, fp, code, msg, response_headers, newurl):
            self.count += 1
            if self.count > 3:
                self.policy_error = EgressError("This API redirected too many times.")
                raise self.policy_error
            try:
                next_url = urljoin(req.full_url, newurl)
                next_host, next_addresses = _validate_url(next_url, domains, allow_private)
                checked[next_host] = next_addresses
            except EgressError as exc:
                self.policy_error = exc
                raise
            return super().redirect_request(req, fp, code, msg, response_headers, newurl)

        def http_error_302(self, req, fp, code, msg, response_headers):
            return super().http_error_302(req, fp, code, msg, response_headers)

        http_error_301 = http_error_302
        http_error_303 = http_error_302
        http_error_307 = http_error_302
        http_error_308 = http_error_302

    redirect = CheckedRedirectHandler()
    opener = build_opener(ProxyHandler({}), PinnedHTTPHandler(), PinnedHTTPSHandler(), redirect)
    request = Request(url, data=body, headers=headers, method=method)
    try:
        response = opener.open(request, timeout=timeout)
    except HTTPError as exc:
        response = exc
    except (URLError, TimeoutError, OSError, EgressError) as exc:
        if redirect.policy_error:
            raise redirect.policy_error
        reason = getattr(exc, "reason", None)
        if isinstance(reason, EgressError):
            raise reason
        raise EgressError("Glacier could not reach this API. Check the address and try again.") from exc
    if redirect.policy_error:
        response.close()
        raise redirect.policy_error
    with response:
        final_host, _ = _validate_url(response.geturl(), domains, allow_private)
        if final_host != host:
            raise EgressError("This API redirected to a different site, so Glacier stopped.")
        payload = response.read(_MAX_DOWNLOAD + 1)
        return response.status, payload


def _fill(text: str, ctx: dict) -> str:
    previous = ctx.get("prev") or {}
    values = {"prev_output": str(previous.get("output") or ""),
              "run": str(ctx.get("run_id") or ""), "env": str(ctx.get("env_id") or "")}
    for key, value in values.items():
        text = text.replace("{" + key + "}", value)
    return text


def _headers(value: str, ctx: dict) -> dict[str, str]:
    result = {}
    for line in str(value or "").splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            raise EgressError("Write each header as Name: value on its own line.")
        name, content = line.split(":", 1)
        name, content = name.strip(), _fill(content.strip(), ctx)
        if not name or "{secret:" in name.lower() or "\r" in name or "\n" in content:
            raise EgressError("Check the header names and values.")
        result[name] = secrets_store.resolve(content)
    return result


def run(ctx: dict) -> dict:
    config = ctx.get("config") or {}
    url = str(config.get("url", "")).strip()
    method = str(config.get("method", "GET")).strip().upper()
    if method not in _METHODS:
        return _failed("Choose GET, POST, PUT, PATCH, or DELETE.")
    if not url:
        return _failed("Add a web address to this step first.")
    domains = allowed_domains(config.get("allowed_sites", ""))
    try:
        timeout = max(0.1, min(120.0, float(config.get("timeout", 20))))
        allow_private = _allow_private(config.get("allow_private_network", "No"))
        # URL placeholders are forbidden even if a templated field could produce one.
        if "{secret:" in url.lower():
            raise EgressError("Remove the secret placeholder from this web address first.")
        headers = _headers(config.get("headers", ""), ctx)
        body_text = _fill(str(config.get("body", "")), ctx)
        body_text = secrets_store.resolve(body_text) if body_text else ""
        body = body_text.encode("utf-8") if body_text and method in {"POST", "PUT", "PATCH", "DELETE"} else None
        if body is not None and str(config.get("body_type", "Text")).strip().lower() == "json":
            json.loads(body_text)
            headers.setdefault("Content-Type", "application/json")
        status, payload = _open(url, method, headers, body, domains, allow_private, timeout)
        try:
            text = payload.decode("utf-8", errors="replace")
        except Exception:
            text = ""
        if str(config.get("body_type", "Text")).strip().lower() == "json":
            try:
                decoded = json.loads(text)
                text = json.dumps(decoded, ensure_ascii=False, indent=2)
            except (json.JSONDecodeError, TypeError):
                pass
        if len(payload) > _MAX_DOWNLOAD:
            text = text[:_MAX_CHARS] + "\n\n[Response body truncated at 1 MB.]"
        expected = str(config.get("expect_status", "2xx")).strip().lower()
        matches = (200 <= status < 300) if expected in {"", "2xx", "default"} else str(status) == expected
        output = f"Status: {status}\n\n{text}"
        if len(output) > _MAX_CHARS:
            output = output[:_MAX_CHARS - 31] + "\n\n[Response text truncated.]"
        output = secrets_store.redact(output)
        if not matches:
            return _failed(f"The API returned status {status}, outside the expected status.")
        return {"state": "done", "output": output, "exit_code": 0,
                "usage": {"model": "http", "route": "user-configured API", "tokens_in": 0, "tokens_out": 0, "cost_usd": 0}}
    except EgressError as exc:
        return _failed(str(exc))
    except Exception:
        return _failed("Glacier could not complete this API request. Check the fields and try again.")


NODE = {
    "catalog": {
        "type": "http_request", "label": "Call a web API",
        "description": "Send a request to an approved API and pass its response to the next step.",
        "fields": [
            {"key": "method", "label": "Method", "default": "GET", "options": ["GET", "POST", "PUT", "PATCH", "DELETE"]},
            {"key": "url", "label": "Web address", "placeholder": "https://api.example.org/items", "default": ""},
            {"key": "allowed_sites", "label": "Allowed sites", "placeholder": "api.example.org", "default": ""},
            {"key": "headers", "label": "Headers", "placeholder": "Authorization: Bearer {secret:API_TOKEN}", "default": "", "optional": True, "multiline": True},
            {"key": "body", "label": "Request body", "placeholder": "Text or JSON; {prev_output}, {run}, {env} are available", "default": "", "optional": True, "multiline": True},
            {"key": "body_type", "label": "Body format", "default": "Text", "options": ["Text", "JSON"], "optional": True},
            {"key": "timeout", "label": "Timeout in seconds", "default": "20", "optional": True},
            {"key": "expect_status", "label": "Expected status", "default": "2xx", "placeholder": "2xx or an exact status such as 201", "optional": True},
            {"key": "allow_private_network", "label": "This API runs on this computer or my network", "default": "No", "options": ["No", "Yes"], "optional": True},
        ],
        "branches": None, "worker": True, "changing_methods": ["POST", "PUT", "PATCH", "DELETE"],
    },
    "run": run,
}
