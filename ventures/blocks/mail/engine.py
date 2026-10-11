from __future__ import annotations

import html
import json
import os
import re
import textwrap
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_AGENCY_TERMS = re.compile(r"\b(official\s+government|government\s+notice|federal\s+agency|department\s+of|irs|osha|cpsc|seal\s+of)\b", re.I)
_TAGS = re.compile(r"<[^>]+>")


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


def _api_url(path: str) -> str:
    base = os.environ.get("LOB_API_BASE_URL", "https://api.lob.com/v1").rstrip("/")
    return f"{base}/{path.lstrip('/')}"


def _lob_request(path: str, *, payload: dict[str, Any] | None = None, params: dict[str, str] | None = None) -> dict[str, Any]:
    key = os.environ.get("LOB_API_KEY", "").strip()
    if not key.startswith("test_"):
        raise ValueError("Lob API key must be a test key (test_ prefix); live sending is disabled")
    url = _api_url(path)
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    request.add_header("Authorization", "Basic " + __import__("base64").b64encode((key + ":").encode()).decode())
    if data:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Lob test API request failed: {exc}") from exc


def verify_address(address: Any) -> dict[str, Any]:
    """Validate an address with Lob; without a test key return an honest uncertain result."""
    fields = _record_address(address)
    if not fields.get("address_line1"):
        return {"verdict": "uncertain", "address": fields, "detail": "street address is missing"}
    if not all(fields.get(key) for key in ("address_city", "address_state", "address_zip")):
        return {"verdict": "uncertain", "address": fields, "detail": "city, state, and ZIP are required for verification"}
    if not os.environ.get("LOB_API_KEY", "").startswith("test_"):
        return {"verdict": "uncertain", "address": fields, "detail": "Lob test key is not configured; address was not verified"}
    result = _lob_request("addresses/validate", params=fields)
    verified = result.get("deliverability") in {"deliverable", "deliverable_unnecessary_unit"}
    return {"verdict": "pass" if verified else "fail", "address": result.get("components") or fields, "detail": result.get("deliverability", "Lob returned no deliverability status"), "lob_address_id": result.get("id")}


def _render_html(source: str, values: dict[str, Any]) -> str:
    rendered = source
    for key, value in values.items():
        rendered = rendered.replace("{{" + str(key) + "}}", html.escape(str(value)))
    return rendered


def _pdf_escape(value: str) -> str:
    return value.encode("latin-1", "replace").decode("latin-1").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _proof_pdf(front: str, back: str, output: Path) -> None:
    """Write a two-page, 4 x 6 inch PDF proof without extra runtime packages."""
    objects: list[bytes] = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R 5 0 R] /Count 2 >>"]
    for markup, content_id in ((front, 4), (back, 6)):
        plain = html.unescape(_TAGS.sub(" ", markup))
        plain = re.sub(r"\s+", " ", plain).strip()
        lines = textwrap.wrap(plain, width=54)[:16] or [" "]
        commands = ["BT", "/F1 11 Tf", "24 395 Td"]
        for line_index, line in enumerate(lines):
            if line_index:
                commands.append("0 -18 Td")
            commands.append(f"({_pdf_escape(line)}) Tj")
        commands.append("ET")
        stream = "\n".join(commands).encode("latin-1", "replace")
        page_id = content_id - 1
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 288 432] /Resources << /Font << /F1 7 0 R >> >> /Contents {content_id} 0 R >>".encode())
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    data = bytearray(b"%PDF-1.4\n% Glacier postcard proof\n")
    offsets = [0]
    for index, body in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{index} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = len(data)
    data.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    output.write_bytes(data)


def postcard(front_html: str, back_html: str, to: Any, from_: Any, *, approval_id: str | None = None,
             output_dir: str | Path | None = None) -> dict[str, Any]:
    """Render a proof; deliver through Lob's test API only with an explicit approval ID."""
    key = os.environ.get("LOB_API_KEY", "").strip()
    if key and not key.startswith("test_"):
        raise ValueError("Lob API key must be a test key (test_ prefix); live sending is disabled")
    destination = Path(output_dir) if output_dir else _default_output_dir()
    destination.mkdir(parents=True, exist_ok=True)
    recipient, sender = _record_address(to), _record_address(from_)
    message_text = front_html + " " + back_html
    sender_name = str(from_.get("name", "") if isinstance(from_, dict) else "").strip()
    check = check_outreach({"sender": sender_name, "address": to}, message_text)
    if check["verdict"] == "fail":
        raise ValueError(f"outreach rule failed: {check['reason']}")
    digest = __import__("hashlib").sha256((json.dumps(recipient, sort_keys=True) + front_html + back_html).encode()).hexdigest()[:14]
    front_path, back_path, proof_path = destination / f"{digest}-front.html", destination / f"{digest}-back.html", destination / f"{digest}-proof.pdf"
    front_path.write_text(front_html, encoding="utf-8")
    back_path.write_text(back_html, encoding="utf-8")
    _proof_pdf(front_html, back_html, proof_path)
    result: dict[str, Any] = {"status": "render_only", "front_html": str(front_path), "back_html": str(back_path), "proof_pdf": str(proof_path), "address_verification": {"verdict": "uncertain", "detail": "not sent; no Lob test key configured" if not key else "not sent; an approval_id is required"}, "outreach_check": check}
    if key.startswith("test_") and approval_id and approval_id.strip():
        verification = verify_address(to)
        result["address_verification"] = verification
        if verification["verdict"] != "pass":
            result["status"] = "not_sent_address_unverified"
            return result
        response = _lob_request("postcards", payload={"to": recipient, "from": sender, "front": front_html, "back": back_html, "size": "6x4", "metadata": {"proof": digest, "approval_id": approval_id.strip()}})
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
