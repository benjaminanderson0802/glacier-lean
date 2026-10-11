from __future__ import annotations

import html
import json
import os
import re
import sys
import shutil
import subprocess
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import httpx
from tempfile import TemporaryDirectory

_AGENCY_TERMS = re.compile(r"\b(official\s+government|government\s+notice|federal\s+agency|department\s+of|irs|osha|cpsc|seal\s+of)\b", re.I)
_TAGS = re.compile(r"<[^>]+>")
_LOB_API_BASE_URL = "https://api.lob.com/v1"


class _LobRequestError(RuntimeError):
    """A safe-to-display failure from Lob's test-only API."""


def _default_output_dir() -> Path:
    return Path(os.environ.get("GLACIER_HOME", Path.home() / ".glacier")) / "ventures" / "mail"


def _record_address(value: Any) -> dict[str, str]:
    if isinstance(value, str):
        return {"address_line1": value}
    if not isinstance(value, dict):
        return {}
    aliases = {"address": "address_line1", "line1": "address_line1", "line2": "address_line2", "zip": "address_zip", "city": "address_city", "state": "address_state"}
    result = {}
    for key, field in value.items():
        target = aliases.get(key, key)
        if field is not None and str(field).strip():
            result[target] = str(field).strip()
    return result


def _suppression_file(path: str | Path | None = None) -> Path:
    return Path(path) if path else _default_output_dir() / "do-not-mail.txt"


def _normalized_address(value: Any) -> str:
    parts = _record_address(value)
    return " ".join(parts.get(k, "") for k in ("address_line1", "address_line2", "address_city", "address_state", "address_zip")).strip().casefold()


def add_to_suppression(address: Any, *, path: str | Path | None = None) -> None:
    """Add a do-not-mail address to the local, rebuildable plain-text suppression list."""
    normalized = _normalized_address(address)
    if not normalized:
        raise ValueError("an address is required for the suppression list")
    target = _suppression_file(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = {line.strip().casefold() for line in target.read_text().splitlines()} if target.exists() else set()
    if normalized not in existing:
        with target.open("a", encoding="utf-8") as stream:
            stream.write(normalized + "\n")


def check_outreach(record: dict[str, Any], message_html: str, *, suppression_path: str | Path | None = None) -> dict[str, str]:
    """Check required sender identity, misleading agency language, and suppression."""
    sender = str(record.get("sender") or "").strip()
    message_text = html.unescape(_TAGS.sub(" ", message_html))
    if not sender:
        return {"verdict": "fail", "reason": "a clear sender name is required"}
    if _AGENCY_TERMS.search(message_text):
        return {"verdict": "fail", "reason": "agency-style wording is not allowed"}
    if sender.casefold() not in message_text.casefold():
        return {"verdict": "fail", "reason": "the postcard must name its sender clearly"}
    normalized = _normalized_address(record.get("address") or record)
    suppression = _suppression_file(suppression_path)
    blocked = {line.strip().casefold() for line in suppression.read_text().splitlines()} if suppression.exists() else set()
    if normalized and (normalized in blocked or any(item.startswith(normalized + ", ") for item in blocked)):
        return {"verdict": "fail", "reason": "recipient is suppressed by the do-not-mail suppression list"}
    return {"verdict": "pass", "reason": "sender is clear, no agency-style wording, and recipient is not suppressed"}


def _secrets_store():
    backend_path = str(Path(__file__).resolve().parents[3] / "glacier" / "backend")
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    import secrets_store  # type: ignore[import-not-found]
    return secrets_store


def _glacier_secret(name: str) -> str | None:
    try:
        return _secrets_store().resolve("{secret:" + name + "}")
    except Exception:
        return None


def _lob_key(secret_getter: Callable[[str], str | None] | None = None) -> str | None:
    try:
        value = (secret_getter or _glacier_secret)("LOB_API_KEY")
    except Exception:
        return None
    return str(value).strip() if value else None


def _check_lob_base_url() -> None:
    configured = os.environ.get("LOB_API_BASE_URL")
    if configured is not None and configured.rstrip("/") != _LOB_API_BASE_URL:
        raise ValueError("Lob API base URL must be the approved HTTPS endpoint")


def _api_url(path: str) -> str:
    _check_lob_base_url()
    if not isinstance(path, str) or not path or "\\" in path or "?" in path or "#" in path:
        raise ValueError("Lob API path is invalid")
    relative = path.lstrip("/")
    parts = relative.split("/")
    if not relative or any(part in {"", ".", ".."} for part in parts):
        raise ValueError("Lob API path is invalid")
    if urllib.parse.unquote(relative) != relative:
        raise ValueError("Lob API path is invalid")
    return f"{_LOB_API_BASE_URL}/{relative}"


def _lob_request(
    path: str,
    *,
    payload: dict[str, Any] | None = None,
    params: dict[str, str] | None = None,
    secret_getter: Callable[[str], str | None] | None = None,
    transport: Any = None,
) -> dict[str, Any]:
    _check_lob_base_url()
    key = _lob_key(secret_getter)
    if not key or not key.startswith("test_"):
        raise ValueError("Lob API key must be a test key (test_ prefix); live sending is disabled")
    url = _api_url(path)
    try:
        method = "POST" if payload is not None else "GET"
        request_options: dict[str, Any] = {
            "params": params,
            "json": payload,
            "auth": (key, ""),
            "timeout": 15,
            "follow_redirects": False,
        }
        if transport is None:
            with httpx.Client(timeout=15, follow_redirects=False, trust_env=False) as client:
                response = client.request(method, url, **request_options)
        else:
            response = transport.request(method, url, **request_options)
        status_code = int(response.status_code)
        if 300 <= status_code < 400:
            raise _LobRequestError("Lob test API redirect was refused")
        if status_code >= 400:
            raise _LobRequestError("Lob test API request failed")
        try:
            result = response.json()
        except Exception:
            raise _LobRequestError("Lob test API returned an invalid response") from None
        if not isinstance(result, dict):
            raise _LobRequestError("Lob test API returned an invalid response")
        return result
    except _LobRequestError:
        raise
    except Exception:
        raise RuntimeError("Lob test API request failed") from None


def verify_address(
    address: Any,
    *,
    secret_getter: Callable[[str], str | None] | None = None,
    transport: Any = None,
) -> dict[str, Any]:
    """Validate an address with Lob; without a test key return an honest uncertain result."""
    fields = _record_address(address)
    if not fields.get("address_line1"):
        return {"verdict": "uncertain", "address": fields, "detail": "street address is missing"}
    if not all(fields.get(key) for key in ("address_city", "address_state", "address_zip")):
        return {"verdict": "uncertain", "address": fields, "detail": "city, state, and ZIP are required for verification"}
    key = _lob_key(secret_getter)
    if not key or not key.startswith("test_"):
        return {"verdict": "uncertain", "address": fields, "detail": "Lob test key is not configured; address was not verified"}
    result = _lob_request("addresses/validate", params=fields, secret_getter=secret_getter, transport=transport)
    verified = result.get("deliverability") in {"deliverable", "deliverable_unnecessary_unit"}
    return {"verdict": "pass" if verified else "fail", "address": result.get("components") or fields, "detail": result.get("deliverability", "Lob returned no deliverability status"), "lob_address_id": result.get("id")}


def _render_html(source: str, values: dict[str, Any]) -> str:
    rendered = source
    for key, value in values.items():
        rendered = rendered.replace("{{" + str(key) + "}}", html.escape(str(value)))
    return rendered


def _proof_browser() -> str:
    """Find the locally installed Chromium used for browser/PDF rendering."""
    configured = os.environ.get("CHROMIUM_PATH", "").strip()
    candidates = [configured]
    candidates.extend(str(path) for path in sorted(Path.home().glob(".cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell"), reverse=True))
    candidates.append("/opt/pw-browsers/chromium")
    candidates.extend(str(path) for path in sorted(Path.home().glob(".cache/ms-playwright/chromium-*/chrome-linux64/chrome"), reverse=True))
    candidates.extend(filter(None, (shutil.which("chromium"), shutil.which("chromium-browser"), shutil.which("google-chrome"))))
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    raise RuntimeError("local postcard proof is blocked: Chromium is not installed; install the pinned Playwright Chromium browser")


def _proof_document(front: str, back: str, sender: dict[str, str], status_id: str, nonce: str) -> str:
    address_parts = [sender.get(key, "") for key in ("address_line1", "address_line2")]
    city_line = " ".join(part for part in (sender.get("address_city", ""), sender.get("address_state", ""), sender.get("address_zip", "")) if part)
    if city_line:
        address_parts.append(city_line)
    sender_details = "<aside class=\"sender-details\"><strong>Return address · " + html.escape(sender.get("name", "Sender not provided")) + "</strong><br>" + "<br>".join(html.escape(part) for part in address_parts if part) + "</aside>"
    notice = "Local review proof · 6 × 4 in · not print-ready"
    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; font-src data:; style-src 'unsafe-inline' data:; script-src 'nonce-{nonce}'">
<title>{notice}</title>
<style>
@page {{ size: 6in 4in; margin: 0 }}
html, body {{ margin: 0; padding: 0; width: 6in; font-family: Arial, sans-serif; color: #111 }}
.proof-page {{ position: relative; box-sizing: border-box; width: 6in; height: 4in; padding: .22in; overflow: hidden; break-after: page; page-break-after: always }}
.proof-page:last-child {{ break-after: auto; page-break-after: auto }}
.copy {{ box-sizing: border-box; width: 100%; height: calc(100% - .48in); overflow: hidden }}
.proof-label {{ position: absolute; left: .22in; bottom: .12in; font: 8pt Arial, sans-serif; color: #444 }}
.sender-details {{ margin-top: .12in; font: 8pt Arial, sans-serif; color: #444 }}
</style></head><body>
<section class="proof-page"><main class="copy">{front}</main><footer class="proof-label">{notice}</footer></section>
<section class="proof-page"><main class="copy">{back}{sender_details}</main><footer class="proof-label">{notice}</footer></section>
<style>
@page {{ size: 6in 4in; margin: 0 }}
html, body {{ margin: 0; padding: 0; width: 6in; font-family: Arial, sans-serif; color: #111 }}
.proof-page {{ position: relative; box-sizing: border-box; width: 6in; height: 4in; padding: .22in; overflow: hidden; break-after: page; page-break-after: always }}
.proof-page:last-child {{ break-after: auto; page-break-after: auto }}
.copy {{ box-sizing: border-box; width: 100%; height: calc(100% - .48in); overflow: hidden }}
.proof-label {{ position: absolute; left: .22in; bottom: .12in; font: 8pt Arial, sans-serif; color: #444 }}
.sender-details {{ margin-top: .12in; font: 8pt Arial, sans-serif; color: #444 }}
</style>
<output id="{status_id}" data-proof-status="pending" hidden></output>
<script nonce="{nonce}">
const status = document.getElementById({json.dumps(status_id)});
const overflowing = [...document.querySelectorAll('.copy')].map((copy, index) => {{
  const bounds = copy.getBoundingClientRect();
  const childOutside = [...copy.querySelectorAll('*')].some((child) => {{
    const rect = child.getBoundingClientRect();
    return rect.left < bounds.left - 1 || rect.right > bounds.right + 1 || rect.top < bounds.top - 1 || rect.bottom > bounds.bottom + 1;
  }});
  const overflow = copy.scrollHeight > copy.clientHeight + 1 || copy.scrollWidth > copy.clientWidth + 1 || childOutside;
  return overflow ? (index === 0 ? 'front' : 'back') : null;
}}).filter(Boolean);
status.dataset.proofStatus = overflowing.length ? 'overflow' : 'ready';
status.dataset.proofSides = overflowing.join(',');
</script></body></html>"""


def _proof_pdf(front: str, back: str, output: Path, sender: dict[str, str] | None = None) -> None:
    """Render a two-page local 6 x 4 inch review PDF through Chromium.

    Raises ValueError when either side cannot fit its page box. The shared
    preview is separate from the co-op workflow's 11.5 x 6.25 inch EDDM proof.
    """
    browser = _proof_browser()
    status_id = "glacier-proof-status"
    nonce = __import__("secrets").token_urlsafe(18)
    document = _proof_document(front, back, sender or {}, status_id, nonce)
    url = "data:text/html;charset=utf-8," + urllib.parse.quote(document, safe="")
    with TemporaryDirectory(prefix="glacier-mail-proof-") as temporary:
        profile = Path(temporary) / "profile"
        common = [browser, "--headless", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
                  "--disable-extensions", "--disable-background-networking", "--disable-sync",
                  "--disable-default-apps", "--no-first-run", "--no-default-browser-check",
                  "--host-resolver-rules=MAP * ~NOTFOUND", f"--user-data-dir={profile}", "--virtual-time-budget=5000"]
        try:
            checked = subprocess.run(common + ["--dump-dom", url], capture_output=True, text=True, timeout=30, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError(f"local postcard proof is blocked: Chromium preflight failed: {exc}") from exc
        if checked.returncode:
            detail = checked.stderr[-500:].strip()
            raise RuntimeError(f"local postcard proof is blocked: Chromium preflight failed: {detail or checked.returncode}")
        status_match = re.search(r'<output id="glacier-proof-status" data-proof-status="(ready|overflow)"(?: data-proof-sides="([^"]*)")?', checked.stdout)
        if not status_match:
            raise RuntimeError("local postcard proof is blocked: Chromium could not inspect the rendered pages")
        if status_match.group(1) == "overflow":
            sides = status_match.group(2) or "front or back"
            raise ValueError(f"postcard proof overflow on {sides}; shorten or reflow the copy before review")
        output.parent.mkdir(parents=True, exist_ok=True)
        try:
            rendered = subprocess.run(common + [f"--print-to-pdf={output}", "--no-pdf-header-footer", url], capture_output=True, text=True, timeout=30, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError(f"local postcard proof is blocked: Chromium PDF rendering failed: {exc}") from exc
        if rendered.returncode or not output.is_file() or output.stat().st_size < 500 or not output.read_bytes().startswith(b"%PDF-"):
            detail = rendered.stderr[-500:].strip()
            raise RuntimeError(f"local postcard proof is blocked: Chromium did not produce a valid PDF: {detail or rendered.returncode}")
        media_boxes = re.findall(rb"/MediaBox\s*\[([^\]]+)\]", output.read_bytes())
        dimensions = []
        for box in media_boxes:
            try:
                dimensions.append(tuple(round(float(value), 2) for value in box.split()))
            except ValueError:
                dimensions.append(())
        if len(dimensions) != 2 or any(box != (0.0, 0.0, 432.0, 288.0) for box in dimensions):
            output.unlink(missing_ok=True)
            raise ValueError("postcard proof overflow: rendered pages did not match the standard 6 x 4 inch preview")


def postcard(front_html: str, back_html: str, to: Any, from_: Any, *, approval_id: str | None = None,
             output_dir: str | Path | None = None,
             secret_getter: Callable[[str], str | None] | None = None,
             transport: Any = None) -> dict[str, Any]:
    """Render a proof; deliver through Lob's test API only with an explicit approval ID."""
    key = _lob_key(secret_getter)
    if key and not key.startswith("test_"):
        raise ValueError("Lob API key must be a test key (test_ prefix); live sending is disabled")
    if not key and os.environ.get("LOB_API_KEY", "").strip().startswith("live_"):
        # Keep legacy live-key rejection without ever using an environment value to authenticate.
        raise ValueError("Lob API key must be a test key (test_ prefix); live sending is disabled")
    destination = Path(output_dir) if output_dir else _default_output_dir()
    destination.mkdir(parents=True, exist_ok=True)
    recipient, sender = _record_address(to), _record_address(from_)
    message_text = front_html + " " + back_html
    sender_name = str(from_.get("name", "") if isinstance(from_, dict) else "").strip()
    check = check_outreach({"sender": sender_name, "address": to}, message_text)
    if check["verdict"] == "fail":
        raise ValueError(f"outreach rule failed: {check['reason']}")
    digest = __import__("hashlib").sha256((json.dumps({"to": recipient, "from": sender}, sort_keys=True) + front_html + back_html).encode()).hexdigest()[:14]
    front_path, back_path, proof_path = destination / f"{digest}-front.html", destination / f"{digest}-back.html", destination / f"{digest}-proof.pdf"
    front_path.write_text(front_html, encoding="utf-8")
    back_path.write_text(back_html, encoding="utf-8")
    proof_info = {"proof_kind": "local_review", "proof_dimensions_inches": {"width": 6, "height": 4}, "proof_notice": "Local review proof only; not print-ready."}
    try:
        _proof_pdf(front_html, back_html, proof_path, sender)
    except ValueError as exc:
        return {"status": "blocked_overflow", "front_html": str(front_path), "back_html": str(back_path), "proof_pdf": None,
                "blocking_reason": str(exc), **proof_info, "outreach_check": check}
    result: dict[str, Any] = {"status": "render_only", "front_html": str(front_path), "back_html": str(back_path), "proof_pdf": str(proof_path), **proof_info, "address_verification": {"verdict": "uncertain", "detail": "not sent; no Lob test key configured" if not key else "not sent; an approval_id is required"}, "outreach_check": check}
    if key and key.startswith("test_") and approval_id and approval_id.strip():
        verification = verify_address(to, secret_getter=secret_getter, transport=transport)
        result["address_verification"] = verification
        if verification["verdict"] != "pass":
            result["status"] = "not_sent_address_unverified"
            return result
        response = _lob_request("postcards", payload={"to": recipient, "from": sender, "front": front_html, "back": back_html, "size": "6x4", "metadata": {"proof": digest, "approval_id": approval_id.strip()}}, secret_getter=secret_getter, transport=transport)
        result.update({"status": "sent_test", "lob_postcard_id": response.get("id"), "delivery_date": response.get("expected_delivery_date"), "approval_id": approval_id.strip()})
    return result


def landing_pages(objects: list[dict[str, Any]], template: str, *, output_dir: str | Path | None = None) -> str:
    """Build one distinct static HTML page per source record using its real values."""
    if not isinstance(objects, list):
        raise TypeError("objects must be a list of source records")
    destination = Path(output_dir) if output_dir else _default_output_dir() / "landing-pages"
    destination.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    index_links = []
    for number, record in enumerate(objects, 1):
        if not isinstance(record, dict) or not record:
            raise ValueError("every landing-page object must be a non-empty record")
        page_id = str(record.get("id") or f"object-{number}")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", page_id) or page_id in seen:
            raise ValueError(f"landing-page id must be unique and path-safe: {page_id}")
        seen.add(page_id)
        page = _render_html(template, record)
        if page == template or not any("{{" + str(key) + "}}" not in page for key in record):
            raise ValueError(f"template did not use any source data for {page_id}")
        (destination / f"{page_id}.html").write_text(page, encoding="utf-8")
        index_links.append(f'<li><a href="{html.escape(page_id)}.html">{html.escape(page_id)}</a></li>')
    (destination / "index.html").write_text("<!doctype html><meta charset=\"utf-8\"><ul>" + "".join(index_links) + "</ul>", encoding="utf-8")
    (destination / "manifest.json").write_text(json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(), "pages": sorted(seen)}, indent=2), encoding="utf-8")
    return str(destination)
