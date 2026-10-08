"""Read a local document or an explicitly allowed web page as plain text."""

from __future__ import annotations

import ipaddress
import io
import os
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener



_PATH_ERROR = "Only files inside this flow's folder can be read"
_MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024


def _validate_url(source: str) -> str:
    parsed = urlsplit(source)
    host = (parsed.hostname or "").lower().rstrip(".")
    try:
        local_host = ipaddress.ip_address(host).is_loopback
    except ValueError:
        local_host = host == "localhost"
    if not host:
        raise ValueError("Use an HTTPS web address")
    if host not in _allowed_hosts():
        raise PermissionError(f"Glacier is not allowed to reach {host}. Add it to the allowed sites first.")
    if parsed.scheme not in (("https", "http") if local_host else ("https",)):
        raise ValueError("Use an HTTPS web address")
    return host


class _AllowlistedRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, new_url):
        _validate_url(new_url)
        return super().redirect_request(req, fp, code, msg, headers, new_url)


def _failed(message: str) -> dict:
    return {"state": "failed", "output": message, "exit_code": 1,
            "usage": {"model": "markitdown", "route": "local/markitdown",
                      "tokens_in": 0, "tokens_out": 0, "cost_usd": 0}}


def _workspace_path(ctx: dict, source: str) -> Path:
    home = Path(ctx["home"]).resolve()
    workspace = (home / "workspaces" / str(ctx["env_id"])).resolve()
    candidate = Path(source)
    if not candidate.is_absolute():
        candidate = workspace / candidate
    candidate = candidate.resolve()
    if not candidate.is_relative_to(workspace):
        raise PermissionError(_PATH_ERROR)
    return candidate


def _allowed_hosts() -> set[str]:
    return {host.strip().lower().rstrip(".") for host in
            os.environ.get("GLACIER_ALLOWED_HOSTS", "").split(",") if host.strip()}


def _read_url(source: str) -> tuple[bytes, str]:
    _validate_url(source)
    request = Request(source, headers={"User-Agent": "Glacier document reader"})
    opener = build_opener(_AllowlistedRedirectHandler())
    with opener.open(request, timeout=10) as response:
        data = response.read(_MAX_DOWNLOAD_BYTES + 1)
        if len(data) > _MAX_DOWNLOAD_BYTES:
            raise ValueError("This document is too large to read")
        content_type = response.headers.get("Content-Type", "")
    return data, content_type


def run(ctx: dict) -> dict:
    config = ctx.get("config") or {}
    source = str(config.get("source", "")).strip()
    if not source:
        return _failed("Choose a file or web address to read")
    try:
        # Document conversion is an occasional operation and pulls in Magika and
        # ONNX Runtime. Keep those libraries out of the backend's startup path.
        from markitdown import MarkItDown

        if source.lower().startswith(("http://", "https://")):
            data, content_type = _read_url(source)
            converted = MarkItDown().convert_stream(io.BytesIO(data), file_extension=_extension(source, content_type))
            text = converted.text_content
        else:
            path = _workspace_path(ctx, source)
            if not path.is_file():
                return _failed(f"File not found: {source}")
            converted = MarkItDown().convert(str(path))
            text = converted.text_content
    except PermissionError as exc:
        return _failed(str(exc))
    except Exception as exc:
        return _failed(f"Could not read this document: {exc}")

    try:
        max_chars = max(0, int(config.get("max_chars", 20000)))
    except (TypeError, ValueError):
        max_chars = 20000
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[Document truncated to the character limit.]"
    return {"state": "done", "output": text, "exit_code": 0,
            "usage": {"model": "markitdown", "route": "local/markitdown",
                      "tokens_in": 0, "tokens_out": 0, "cost_usd": 0}}


def _extension(source: str, content_type: str) -> str | None:
    suffix = Path(urlsplit(source).path).suffix
    if suffix:
        return suffix
    media = content_type.split(";", 1)[0].strip().lower()
    return {"text/html": ".html", "text/csv": ".csv", "text/plain": ".txt"}.get(media)


NODE = {
    "catalog": {
        "type": "read_document",
        "label": "Read document",
        "description": "Turn a file or allowed web page into plain text for the next step.",
        "fields": [
            {"key": "source", "label": "File or web address", "placeholder": "report.pdf or https://example.org", "default": ""},
            {"key": "max_chars", "label": "Maximum characters", "placeholder": "20000", "default": "20000"},
        ],
        "branches": None,
        "worker": True,
    },
    "run": run,
}
