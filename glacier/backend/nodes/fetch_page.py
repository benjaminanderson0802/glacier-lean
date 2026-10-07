"""Fetch one approved web page and convert it to plain text."""

from __future__ import annotations

import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

import files_store
from egress import EgressError, allowed_domains, validate_url

_MAX_DOWNLOAD = 5 * 1024 * 1024
_MAX_CHARS = 20_000
_ALLOWED_TYPES = {"text/html", "text/plain", "application/pdf", "application/json", "text/markdown"}
_USER_AGENT = "Glacier (local automation)"


def _failed(message: str) -> dict:
    return {"state": "failed", "output": message, "exit_code": 1,
            "usage": {"model": "markitdown", "route": "local/markitdown",
                      "tokens_in": 0, "tokens_out": 0, "cost_usd": 0}}


class _CheckedRedirectHandler(HTTPRedirectHandler):
    def __init__(self, domains: set[str]):
        super().__init__()
        self.domains = domains
        self.redirect_count = 0
        self.policy_error: EgressError | None = None

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.redirect_count += 1
        if self.redirect_count > 3:
            raise EgressError("This page redirected too many times.")
        try:
            validate_url(urljoin(req.full_url, newurl), self.domains)
        except EgressError as exc:
            self.policy_error = exc
            raise
        return super().redirect_request(req, fp, code, msg, headers, newurl)

    def http_error_302(self, req, fp, code, msg, headers):
        return super().http_error_302(req, fp, code, msg, headers)

    http_error_301 = http_error_302
    http_error_303 = http_error_302
    http_error_307 = http_error_302
    http_error_308 = http_error_302


def _fetch(url: str, domains: set[str]) -> tuple[bytes, str, str, int]:
    validate_url(url, domains)
    handler = _CheckedRedirectHandler(domains)
    opener = build_opener(handler)
    request = Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        response = opener.open(request, timeout=10)
    except HTTPError as exc:
        response = exc
    except (URLError, TimeoutError, OSError) as exc:
        if handler.policy_error:
            raise handler.policy_error
        if isinstance(getattr(exc, "reason", None), EgressError):
            raise exc.reason
        raise EgressError("Glacier could not reach this page. Check the address and try again.") from exc
    with response:
        final_url = response.geturl()
        validate_url(final_url, domains)
        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type not in _ALLOWED_TYPES:
            raise EgressError("This page type cannot be read. Use HTML, plain text, PDF, JSON, or Markdown.")
        body = response.read(_MAX_DOWNLOAD + 1)
        if len(body) > _MAX_DOWNLOAD:
            raise EgressError("This page is too large to read (the limit is 5 MB).")
        return body, content_type, final_url, response.status


def _convert_download(data: bytes, content_type: str) -> str:
    suffix = {"text/html": ".html", "text/plain": ".txt", "application/pdf": ".pdf",
              "application/json": ".json", "text/markdown": ".md"}[content_type]
    with tempfile.TemporaryDirectory(prefix="glacier-fetch-") as folder:
        path = Path(folder) / ("page" + suffix)
        path.write_bytes(data)
        return files_store._convert_in_child(path)


def run(ctx: dict) -> dict:
    config = ctx.get("config") or {}
    url = str(config.get("url", "")).strip()
    domains = allowed_domains(config.get("allowed_sites", ""))
    if not url:
        return _failed("Add a web address to this step first.")
    if not domains:
        return _failed("Add this site to the step's allowed sites first.")
    try:
        data, content_type, final_url, status = _fetch(url, domains)
        text = _convert_download(data, content_type)
    except EgressError as exc:
        return _failed(str(exc))
    except Exception:
        return _failed("Glacier could not turn this page into text. Check the address and file type.")
    header = f"Final URL: {final_url}\nStatus: {status}\n\n"
    available = max(0, _MAX_CHARS - len(header))
    truncated = len(text) > available
    output = header + text[:available]
    if truncated:
        note = "\n\n[Page text truncated.]"
        output = output[:_MAX_CHARS - len(note)] + note
    return {"state": "done", "output": output, "exit_code": 0,
            "usage": {"model": "markitdown", "route": "local/markitdown",
                      "tokens_in": 0, "tokens_out": 0, "cost_usd": 0}}


NODE = {
    "catalog": {
        "type": "fetch_page", "label": "Read a web page",
        "description": "Fetch one approved web page and turn it into text for the next step.",
        "fields": [
            {"key": "url", "label": "Web address", "placeholder": "https://example.org/page", "default": ""},
            {"key": "allowed_sites", "label": "Allowed sites", "placeholder": "example.org, docs.python.org", "default": ""},
        ],
        "branches": None, "worker": True,
    },
    "run": run,
}
