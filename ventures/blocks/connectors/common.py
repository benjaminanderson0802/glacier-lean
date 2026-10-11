"""Shared HTTP behavior for read-only platform connector clients."""

from __future__ import annotations

import time
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import httpx


class ConnectorError(RuntimeError):
    """A safe-to-display connector error that never includes credentials."""


class UnauthorizedError(ConnectorError):
    """Authentication failed; an OAuth client may refresh once and retry."""


def glacier_secret(name: str) -> str | None:
    """Resolve a saved Glacier secret from the OS keychain at request time."""
    try:
        secrets_store = _secrets_store()
        return secrets_store.resolve("{secret:" + name + "}")
    except Exception:
        return None


def glacier_secret_writer(name: str, value: str) -> None:
    """Persist an OAuth token through Glacier's keychain-backed store."""
    _secrets_store().set(name, value)


def _secrets_store():
    try:
        from glacier.backend import secrets_store
        return secrets_store
    except ModuleNotFoundError as exc:
        if exc.name != "app_paths":
            raise
    backend_path = str(Path(__file__).resolve().parents[3] / "glacier" / "backend")
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    import secrets_store  # type: ignore[no-redef]
    return secrets_store


def _retry_delay(response: httpx.Response | None, attempt: int) -> float:
    if response is not None:
        value = response.headers.get("Retry-After", "")
        try:
            return min(30.0, max(0.0, float(value)))
        except ValueError:
            pass
    return min(8.0, 0.5 * (2**attempt))


class ReadOnlyClient:
    """GET-only REST and query-only GraphQL transport with bounded retries."""

    def __init__(
        self,
        *,
        secret_name: str,
        secret_resolver: Callable[[str], str | None] = glacier_secret,
        access_token: str | None = None,
        api_key: str | None = None,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 20.0,
        max_attempts: int = 3,
        request_interval: float = 0.0,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._secret_name = secret_name
        self._secret_resolver = secret_resolver
        self._access_token = access_token
        self._api_key = api_key
        self._transport = transport
        self._timeout = timeout
        self._max_attempts = max(1, min(5, max_attempts))
        self._request_interval = max(0.0, request_interval)
        self._monotonic = monotonic
        self._last_request_at: float | None = None
        self._sleep = sleep
        self._http: httpx.Client | None = None

    def _credential(self) -> str:
        value = self._access_token or self._api_key
        if value:
            return value
        try:
            value = self._secret_resolver(self._secret_name)
        except Exception:
            value = None
        if not value:
            raise ConnectorError(f"The '{self._secret_name}' key is not configured in Glacier's secret store.")
        return value

    def _client(self) -> httpx.Client:
        if self._http is None:
            self._http = httpx.Client(transport=self._transport, timeout=self._timeout)
        return self._http

    def close(self) -> None:
        if self._http is not None:
            self._http.close()
            self._http = None

    def _request(self, method: str, url: str, *, headers: Mapping[str, str], params: Mapping[str, Any] | None = None, json_body: Any = None, form_body: Mapping[str, str] | None = None, auth_post: bool = False) -> httpx.Response:
        graphql_read = method.upper() == "POST" and json_body and "query" in json_body and "mutation" not in json_body["query"].lower()
        if method.upper() != "GET" and not graphql_read and not (auth_post and method.upper() == "POST" and form_body is not None):
            raise ConnectorError("This connector is read-only; writes are disabled.")
        now = self._monotonic()
        if self._request_interval and self._last_request_at is not None:
            wait = self._request_interval - (now - self._last_request_at)
            if wait > 0:
                self._sleep(wait)
        self._last_request_at = self._monotonic()
        last_response: httpx.Response | None = None
        for attempt in range(self._max_attempts):
            try:
                response = self._client().request(method, url, headers=dict(headers), params=params, json=json_body, data=form_body)
            except httpx.TransportError:
                if attempt + 1 >= self._max_attempts:
                    raise ConnectorError("The platform could not be reached after bounded retries.") from None
                self._sleep(_retry_delay(None, attempt))
                continue
            if response.status_code == 429 or 500 <= response.status_code <= 599:
                last_response = response
                if attempt + 1 < self._max_attempts:
                    self._sleep(_retry_delay(response, attempt))
                    continue
            if response.is_error:
                self._raise_http_error(response)
            return response
        status = last_response.status_code if last_response is not None else "unknown"
        raise ConnectorError(f"The platform remained unavailable after bounded retries (HTTP {status}).")

    def _raise_http_error(self, response: httpx.Response) -> None:
        """Raise a safe error for an HTTP failure without exposing response content."""
        if response.status_code == 401:
            raise UnauthorizedError("The platform rejected the saved credential (HTTP 401).")
        raise ConnectorError(f"The platform returned HTTP {response.status_code}.")

    @staticmethod
    def _json(response: httpx.Response) -> Any:
        try:
            payload = response.json()
        except ValueError:
            raise ConnectorError("The platform returned an unreadable response.") from None
        if isinstance(payload, dict) and payload.get("errors"):
            first = payload["errors"][0]
            code = ((first.get("extensions") or {}).get("code") if isinstance(first, dict) else None)
            if code in {"THROTTLED", "RATE_LIMITED"}:
                raise ConnectorError("The platform throttled this read; retry after a short wait.")
            raise ConnectorError("The platform rejected the read query.")
        return payload

    def _graphql(self, url: str, headers: Mapping[str, str], query: str, variables: Mapping[str, Any] | None) -> dict[str, Any]:
        body = {"query": query, "variables": dict(variables or {})}
        for attempt in range(self._max_attempts):
            response = self._request("POST", url, headers=headers, json_body=body)
            try:
                payload = response.json()
            except ValueError:
                raise ConnectorError("The platform returned an unreadable response.") from None
            errors = payload.get("errors") if isinstance(payload, dict) else None
            throttled = any(
                isinstance(error, dict)
                and (error.get("extensions") or {}).get("code") in {"THROTTLED", "RATE_LIMITED"}
                for error in (errors or [])
            )
            if throttled and attempt + 1 < self._max_attempts:
                self._sleep(_retry_delay(response, attempt))
                continue
            if errors:
                raise ConnectorError("The platform throttled this read; retry later." if throttled else "The platform rejected the read query.")
            return payload.get("data") or {}
        raise ConnectorError("The platform remained throttled after bounded retries.")

    def __repr__(self) -> str:
        return f"{type(self).__name__}(secret_name={self._secret_name!r}, read_only=True)"
