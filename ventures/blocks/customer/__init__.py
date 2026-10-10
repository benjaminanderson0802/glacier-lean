"""Local customer accounts, test-mode billing, signing, status pages, and support."""
from __future__ import annotations

import email
import hashlib
import html
import imaplib
import ipaddress
import json
import os
import re
import sqlite3
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from email.header import decode_header
from email.policy import default
from email.utils import parseaddr
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


class CustomerError(RuntimeError):
    """A safe-to-display customer layer error."""


_TEST_API_BASE = "https://api.stripe.com"


def _default_home() -> Path:
    return Path(os.environ.get("GLACIER_HOME", "data")).expanduser().resolve() / "ventures"


def _database_path(db_path: str | Path | None) -> Path:
    path = Path(db_path) if db_path is not None else _default_home() / "customers.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = _database_path(db_path)
    connection = sqlite3.connect(path)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS customers (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL,
            created_at TEXT NOT NULL, metadata_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS signature_requests (
            id TEXT PRIMARY KEY, customer_id TEXT, signer_json TEXT NOT NULL,
            source_path TEXT NOT NULL, source_sha256 TEXT NOT NULL,
            page_path TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL,
            signed_at TEXT, pdf_path TEXT, audit_path TEXT
        );
        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT NOT NULL,
            subject_id TEXT NOT NULL, approval_id TEXT, details_json TEXT NOT NULL,
            happened_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS support_messages (
            id TEXT PRIMARY KEY, message_id TEXT, sender TEXT NOT NULL,
            subject TEXT NOT NULL, body TEXT NOT NULL, received_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS support_drafts (
            id TEXT PRIMARY KEY, message_id TEXT NOT NULL, body TEXT NOT NULL,
            status TEXT NOT NULL, created_at TEXT NOT NULL,
            approved_at TEXT, approval_id TEXT
        );
        """
    )
    connection.commit()
    return connection


@contextmanager
def _database(db_path: str | Path | None = None):
    connection = _connect(db_path)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_customer(details: dict[str, Any], db_path: str | Path | None = None) -> dict[str, Any]:
    name = str(details.get("name", "")).strip()
    address = str(details.get("email", "")).strip()
    if not name or not address or "@" not in address:
        raise CustomerError("Customer name and a valid email address are required.")
    item = {"id": str(uuid.uuid4()), "name": name, "email": address,
            "created_at": _now(), "metadata": details.get("metadata", {})}
    with _database(db_path) as db:
        db.execute("INSERT INTO customers VALUES (?, ?, ?, ?, ?)",
                   (item["id"], name, address, item["created_at"], json.dumps(item["metadata"])))
    return item


def get_customer(customer_id: str, db_path: str | Path | None = None) -> dict[str, Any] | None:
    with _database(db_path) as db:
        row = db.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
    if row is None:
        return None
    return {"id": row["id"], "name": row["name"], "email": row["email"],
            "created_at": row["created_at"], "metadata": json.loads(row["metadata_json"])}


def _secret(name: str) -> str | None:
    """Resolve through Glacier's keyring-backed secret store; never read env values."""
    backend = str(Path(__file__).resolve().parents[3] / "glacier" / "backend")
    if backend not in sys.path:
        sys.path.insert(0, backend)
    try:
        import secrets_store  # type: ignore[import-not-found]
        return secrets_store.resolve("{secret:" + name + "}")
    except (ValueError, ImportError, RuntimeError):
        return None


def configure_stripe_for_tests(api_base: str | None) -> None:
    """Set a local recorded-response endpoint for tests; production stays on Stripe."""
    global _TEST_API_BASE
    if not api_base:
        _TEST_API_BASE = "https://api.stripe.com"
        return
    parsed = urlsplit(api_base)
    try:
        loopback = parsed.hostname == "localhost" or bool(ipaddress.ip_address(parsed.hostname or "").is_loopback)
    except ValueError:
        loopback = False
    if parsed.scheme != "http" or not loopback or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise CustomerError("Recorded Stripe endpoints must use plain HTTP on localhost only.")
    _TEST_API_BASE = api_base.rstrip("/")


def _stripe_request(path: str, fields: dict[str, str], key: str,
                    idempotency_key: str | None = None) -> dict[str, Any]:
    headers = {"Authorization": "Bearer " + key, "Content-Type": "application/x-www-form-urlencoded"}
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    request = Request(
        _TEST_API_BASE + path,
        data=urlencode(fields).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            error_data = json.loads(exc.read().decode("utf-8"))
            message = error_data.get("error", {}).get("message", "Stripe request failed")
        except Exception:
            message = "Stripe request failed"
        raise CustomerError(f"Stripe test-mode request failed: {message}") from None
    except (URLError, TimeoutError, json.JSONDecodeError):
        raise CustomerError("Could not reach Stripe. Check the network and try again.") from None
    if not isinstance(data, dict):
        raise CustomerError("Stripe returned an invalid response.")
    return data


def _require_test_key(secret_getter: Callable[[str], str | None] | None) -> str:
    key = (secret_getter or _secret)("STRIPE_SECRET_KEY")
    if not key:
        raise CustomerError("Stripe is not configured. Add STRIPE_SECRET_KEY in Glacier Settings > Secrets.")
    if not key.startswith("sk_test_"):
        raise CustomerError("Only a Stripe test-mode key is allowed by this customer block.")
    return key


def checkout_link(plan: str, *, secret_getter: Callable[[str], str | None] | None = None,
                  plans: dict[str, dict[str, str]] | None = None,
                  approval_id: str | None = None,
                  customer_id: str | None = None,
                  db_path: str | Path | None = None) -> str:
    if approval_id is not None and not approval_id.strip():
        raise CustomerError("An approval ID must not be blank.")
    key = _require_test_key(secret_getter)
    plan_config = (plans or {}).get(plan)
    if plan_config is None:
        env_name = "STRIPE_PRICE_" + re.sub(r"[^A-Z0-9]+", "_", plan.upper()).strip("_")
        price_id = os.environ.get(env_name, "")
        plan_config = {"price_id": price_id, "mode": "subscription"}
    price_id = plan_config.get("price_id", "")
    if not price_id:
        raise CustomerError(f"No Stripe test price is configured for plan '{plan}'.")
    mode = plan_config.get("mode", "subscription")
    if mode not in {"subscription", "payment"}:
        raise CustomerError("Stripe plan mode must be 'subscription' or 'payment'.")
    success_url = plan_config.get("success_url", "http://localhost:8765/customer/success?session_id={CHECKOUT_SESSION_ID}")
    cancel_url = plan_config.get("cancel_url", "http://localhost:8765/customer/cancelled")
    for target in (success_url, cancel_url):
        parsed_target = urlsplit(target)
        local_http = parsed_target.scheme == "http" and parsed_target.hostname in {"localhost", "127.0.0.1", "::1"}
        if not (parsed_target.scheme == "https" or local_http) or not parsed_target.hostname:
            raise CustomerError("Checkout return links must use HTTPS, or localhost HTTP for a local test.")
    fields = {
        "mode": mode,
        "line_items[0][price]": price_id,
        "line_items[0][quantity]": "1",
        "success_url": success_url,
        "cancel_url": cancel_url,
    }
    if customer_id:
        fields["client_reference_id"] = customer_id
        fields["metadata[customer_id]"] = customer_id
    if approval_id:
        fields["metadata[approval_id]"] = approval_id.strip()
    response = _stripe_request("/v1/checkout/sessions", fields, key)
    url = response.get("url")
    if not isinstance(url, str) or not url.startswith("https://"):
        raise CustomerError("Stripe did not return a secure checkout link.")
    with _database(db_path) as db:
        db.execute("INSERT INTO audit_events(event, subject_id, details_json, happened_at) VALUES (?, ?, ?, ?)",
                   ("stripe_checkout_created", str(response.get("id", "unknown")),
                    json.dumps({"plan": plan, "customer_id": customer_id, "mode": mode,
                                "approval_id": approval_id.strip() if approval_id else None}), _now()))
    return url


def refund(payment_intent: str, *, approval_id: str,
           secret_getter: Callable[[str], str | None] | None = None,
           db_path: str | Path | None = None) -> dict[str, Any]:
    if not approval_id.strip():
        raise CustomerError("A recorded owner approval is required before a refund.")
    key = _require_test_key(secret_getter)
    result = _stripe_request("/v1/refunds", {"payment_intent": payment_intent,
                                              "metadata[approval_id]": approval_id}, key,
                             idempotency_key="glacier-refund-" + hashlib.sha256(approval_id.encode()).hexdigest())
    with _database(db_path) as db:
        db.execute("INSERT INTO audit_events(event, subject_id, approval_id, details_json, happened_at) VALUES (?, ?, ?, ?, ?)",
                   ("stripe_refund", str(result.get("id", payment_intent)), approval_id,
                    json.dumps({"payment_intent": payment_intent, "status": result.get("status")}), _now()))
    return result


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _make_audit_pdf(target: Path, lines: list[str]) -> None:
    """Emit a small, dependency-free one-page PDF signature certificate."""
    commands = ["BT", "/F1 11 Tf", "50 790 Td", "14 TL"]
    for index, line in enumerate(lines):
        if index:
            commands.append("T*")
        commands.append("(" + _pdf_escape(line[:150]) + ") Tj")
    commands.append("ET")
    stream = "\n".join(commands).encode("latin-1", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    target.write_bytes(output)
    try:
        target.chmod(0o600)
    except OSError:
        pass


def request_signature(doc_path: str | Path, signer: dict[str, Any], *,
                      data_dir: str | Path | None = None,
                      customer_id: str | None = None) -> dict[str, str]:
    source = Path(doc_path).expanduser().resolve()
    if not source.is_file():
        raise CustomerError("The document to sign could not be found.")
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    signer_name = str(signer.get("name", "")).strip()
    if not signer_name:
        raise CustomerError("A signer name is required.")
    root = Path(data_dir) if data_dir else _default_home()
    pages = root / "signature-pages"
    pages.mkdir(parents=True, exist_ok=True)
    request_id = str(uuid.uuid4())
    page = pages / f"{request_id}.html"
    safe_name = html.escape(signer_name)
    body = f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Review and sign</title>
<body><main><h1>Review and sign</h1><p>Document: {html.escape(source.name)}</p><p>Document fingerprint: <code>{digest}</code></p><p>Signing creates a timestamped PDF certificate and an audit record linked to this document fingerprint.</p>
<form method="post" action="http://127.0.0.1:8765/sign/{request_id}"><label>Your full name <input name="typed_name" value="{safe_name}" required></label><label><input type="checkbox" name="consent" value="yes" required> I agree to sign this document electronically.</label><button type="submit">Sign document</button></form>
</main></body></html>"""
    page.write_text(body, encoding="utf-8")
    try:
        page.chmod(0o600)
    except OSError:
        pass
    with _database(data_dir and (Path(data_dir) / "customers.db")) as db:
        db.execute("INSERT INTO signature_requests(id, customer_id, signer_json, source_path, source_sha256, page_path, status, created_at) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)",
                   (request_id, customer_id, json.dumps({"name": signer_name, "email": signer.get("email", "")}),
                    str(source), digest, str(page), _now()))
    return {"id": request_id, "page_path": str(page), "url": f"http://127.0.0.1:8765/signature/{request_id}",
            "document_sha256": digest}


def sign_document(request_id: str, *, typed_name: str, consent: bool,
                  data_dir: str | Path | None = None) -> dict[str, str]:
    if not consent:
        raise CustomerError("Explicit electronic-signature consent is required.")
    typed_name = typed_name.strip()
    if not typed_name:
        raise CustomerError("The signer must enter their full name.")
    root = Path(data_dir) if data_dir else _default_home()
    with _database(root / "customers.db") as db:
        row = db.execute("SELECT * FROM signature_requests WHERE id = ?", (request_id,)).fetchone()
        if row is None:
            raise CustomerError("This signature request was not found.")
        if row["status"] != "pending":
            raise CustomerError("This signature request has already been completed.")
        expected = json.loads(row["signer_json"])["name"]
        if typed_name.casefold() != expected.casefold():
            raise CustomerError("The entered name does not match the requested signer.")
        source = Path(row["source_path"])
        if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != row["source_sha256"]:
            raise CustomerError("The document changed after the signature request was prepared.")
        signed_at = _now()
        output = root / "signed"
        output.mkdir(parents=True, exist_ok=True)
        pdf_path = output / f"{request_id}-signed.pdf"
        audit_path = output / f"{request_id}-audit.json"
        lines = ["Electronic signature certificate", f"Document: {source.name}",
                 f"Document SHA-256: {row['source_sha256']}", f"Signer: {typed_name}",
                 f"Signer email: {json.loads(row['signer_json']).get('email', '')}",
                 f"Consent: yes", f"Signed at (UTC): {signed_at}",
                 f"Signature request: {request_id}", "Original document is identified by its SHA-256 fingerprint."]
        _make_audit_pdf(pdf_path, lines)
        pdf_digest = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
        audit = {"event": "electronic_signature", "request_id": request_id,
                 "document": source.name, "document_sha256": row["source_sha256"],
                 "signer": typed_name, "signer_email": json.loads(row["signer_json"]).get("email", ""),
                 "consent": True, "signed_at": signed_at, "signed_pdf": str(pdf_path),
                 "signed_pdf_sha256": pdf_digest}
        audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
        try:
            audit_path.chmod(0o600)
        except OSError:
            pass
        db.execute("UPDATE signature_requests SET status='signed', signed_at=?, pdf_path=?, audit_path=? WHERE id=?",
                   (signed_at, str(pdf_path), str(audit_path), request_id))
        db.execute("INSERT INTO audit_events(event, subject_id, details_json, happened_at) VALUES (?, ?, ?, ?)",
                   ("signature_completed", request_id, json.dumps({"document_sha256": row["source_sha256"],
                                                                   "signed_pdf_sha256": pdf_digest}), signed_at))
    return {"pdf_path": str(pdf_path), "audit_path": str(audit_path), "signed_at": signed_at}


def _status_html(customer: dict[str, Any], updates: list[dict[str, Any]]) -> str:
    rows = "".join("<li><strong>" + html.escape(str(item.get("status", "Update"))) + "</strong>: " +
                   html.escape(str(item.get("detail", ""))) + " <time>" +
                   html.escape(str(item.get("updated_at", ""))) + "</time></li>" for item in updates)
    return ("<!doctype html><html lang=\"en\"><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Customer status</title>"
            "<main><h1>Status for " + html.escape(customer["name"]) + "</h1><ul>" + rows +
            "</ul><p>This page is a status summary, not a legal conclusion.</p></main></html>")


def status_page(customer_id: str, *, updates: list[dict[str, Any]] | None = None,
                data_dir: str | Path | None = None,
                db_path: str | Path | None = None) -> str:
    customer = get_customer(customer_id, db_path=db_path or ((Path(data_dir) / "customers.db") if data_dir else None))
    if customer is None:
        raise CustomerError("Customer account was not found.")
    pages = (Path(data_dir) if data_dir else _default_home()) / "status-pages"
    pages.mkdir(parents=True, exist_ok=True)
    page = pages / f"{customer_id}.html"
    page.write_text(_status_html(customer, updates or []), encoding="utf-8")
    try:
        page.chmod(0o600)
    except OSError:
        pass
    return str(page)


def _decode_header(value: str | None) -> str:
    if not value:
        return ""
    return "".join((part.decode(charset or "utf-8", errors="replace") if isinstance(part, bytes) else part)
                   for part, charset in decode_header(value))


def _message_body(message: email.message.Message) -> str:
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "text/plain" and part.get_content_disposition() != "attachment":
                try:
                    return part.get_content()
                except Exception:
                    return ""
        return ""
    try:
        return message.get_content()
    except Exception:
        payload = message.get_payload(decode=True) or b""
        return payload.decode(message.get_content_charset() or "utf-8", errors="replace")


def _support_config() -> dict[str, str]:
    config_path = _default_home() / "support.json"
    try:
        value = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError):
        raise CustomerError("The saved support inbox settings cannot be read.") from None
    return value if isinstance(value, dict) else {}


def configure_support_inbox(config: dict[str, str], *, data_dir: str | Path | None = None) -> str:
    """Save IMAP connection metadata only; password values stay in Glacier's keyring."""
    allowed = {"host", "username", "mailbox", "password_secret"}
    if set(config) - allowed:
        raise CustomerError("Support settings may only include host, username, mailbox, and a secret name.")
    if not config.get("host") or not config.get("username") or not config.get("password_secret"):
        raise CustomerError("Support settings need an IMAP host, username, and password secret name.")
    root = Path(data_dir) if data_dir else _default_home()
    root.mkdir(parents=True, exist_ok=True)
    path = root / "support.json"
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return str(path)


def support_inbox(*, config: dict[str, Any] | None = None,
                  secret_getter: Callable[[str], str | None] | None = None,
                  imap_factory: Callable[[str], Any] | None = None,
                  db_path: str | Path | None = None) -> list[dict[str, str]]:
    cfg = config if config is not None else _support_config()
    for name in ("host", "username", "password_secret"):
        if not cfg.get(name):
            raise CustomerError("IMAP support settings are incomplete: host, username, and password secret are required.")
    password = (secret_getter or _secret)(str(cfg["password_secret"]))
    if not password:
        raise CustomerError(f"Missing IMAP password secret '{cfg['password_secret']}'. Add it in Glacier Settings > Secrets.")
    client = (imap_factory or imaplib.IMAP4_SSL)(str(cfg["host"]))
    try:
        client.login(str(cfg["username"]), password)
        status, _ = client.select(str(cfg.get("mailbox", "INBOX")), readonly=True)
        if status != "OK":
            raise CustomerError("The support inbox could not be opened.")
        status, ids = client.search(None, "ALL")
        if status != "OK":
            raise CustomerError("Support messages could not be listed.")
        result = []
        with _database(db_path) as db:
            for message_number in ids[0].split()[-100:]:
                status, parts = client.fetch(message_number, "(RFC822)")
                if status != "OK":
                    continue
                raw = next((part[1] for part in parts if isinstance(part, tuple)), b"")
                parsed = email.message_from_bytes(raw, policy=default)
                message_id = str(parsed.get("Message-ID", "")).strip()
                stable_id = message_id or hashlib.sha256(raw).hexdigest()
                msg = {"id": stable_id, "sender": _decode_header(parsed.get("From")),
                       "subject": _decode_header(parsed.get("Subject")), "body": _message_body(parsed),
                       "received_at": _decode_header(parsed.get("Date"))}
                db.execute("INSERT OR IGNORE INTO support_messages VALUES (?, ?, ?, ?, ?, ?)",
                           (stable_id, message_id, msg["sender"], msg["subject"], msg["body"], msg["received_at"]))
                result.append(msg)
        return result
    finally:
        try:
            client.logout()
        except Exception:
            pass


def draft_reply(message_id: str, body: str, *, db_path: str | Path | None = None) -> dict[str, str]:
    if not body.strip():
        raise CustomerError("A reply draft cannot be empty.")
    draft_id = str(uuid.uuid4())
    created = _now()
    with _database(db_path) as db:
        if not db.execute("SELECT 1 FROM support_messages WHERE id=?", (message_id,)).fetchone():
            raise CustomerError("Support message was not found. Read the inbox before drafting a reply.")
        db.execute("INSERT INTO support_drafts VALUES (?, ?, ?, 'pending_approval', ?, NULL, NULL)",
                   (draft_id, message_id, body.strip(), created))
    return {"id": draft_id, "message_id": message_id, "body": body.strip(), "status": "pending_approval"}


def send_reply(draft_id: str, *, approval_id: str, smtp_sender: Callable[[str, str], Any] | None = None,
               db_path: str | Path | None = None) -> None:
    if not approval_id.strip():
        raise CustomerError("Owner approval is required before sending a support reply.")
    if smtp_sender is None:
        raise CustomerError("An approved SMTP sender is required; no reply was sent.")
    with _database(db_path) as db:
        draft = db.execute("SELECT * FROM support_drafts WHERE id=?", (draft_id,)).fetchone()
        if not draft or draft["status"] != "pending_approval":
            raise CustomerError("This reply is missing or is no longer pending approval.")
        message = db.execute("SELECT * FROM support_messages WHERE id=?", (draft["message_id"],)).fetchone()
        if not message:
            raise CustomerError("The support message for this draft no longer exists.")
        recipient = parseaddr(message["sender"])[1]
        if not recipient:
            raise CustomerError("The sender address could not be parsed; no reply was sent.")
        smtp_sender(recipient, draft["body"])
        db.execute("UPDATE support_drafts SET status='sent', approved_at=?, approval_id=? WHERE id=?",
                   (_now(), approval_id, draft_id))
        db.execute("INSERT INTO audit_events(event, subject_id, approval_id, details_json, happened_at) VALUES (?, ?, ?, ?, ?)",
                   ("support_reply_sent", draft_id, approval_id, json.dumps({"message_id": message["id"]}), _now()))


def list_support_drafts(*, db_path: str | Path | None = None) -> list[dict[str, str]]:
    with _database(db_path) as db:
        rows = db.execute("SELECT * FROM support_drafts ORDER BY created_at DESC").fetchall()
    return [{"id": row["id"], "message_id": row["message_id"], "body": row["body"],
             "status": row["status"], "created_at": row["created_at"]} for row in rows]


def create_signature_server(data_dir: str | Path | None = None, *, host: str = "127.0.0.1", port: int = 8765):
    """Create an HTTP server for signature pages; loopback binding is the safe default."""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import parse_qs

    root = Path(data_dir) if data_dir else _default_home()

    class SignaturePageHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/customer/success"):
                payload = b"<!doctype html><meta charset=utf-8><title>Payment complete</title><h1>Payment complete</h1><p>Return to Glacier to view your customer status.</p>"
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return
            if self.path == "/customer/cancelled":
                payload = b"<!doctype html><meta charset=utf-8><title>Checkout cancelled</title><h1>Checkout cancelled</h1><p>No payment was completed.</p>"
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return
            match = re.fullmatch(r"/signature/([a-f0-9-]{36})", self.path)
            if not match:
                self.send_error(404)
                return
            with _database(root / "customers.db") as db:
                row = db.execute("SELECT page_path, status FROM signature_requests WHERE id=?", (match.group(1),)).fetchone()
            if not row or row["status"] != "pending":
                self.send_error(404)
                return
            try:
                page = Path(row["page_path"]).read_text(encoding="utf-8")
            except OSError:
                self.send_error(404)
                return
            page = page.replace("http://127.0.0.1:8765/sign/", f"http://{self.server.server_address[0]}:{self.server.server_address[1]}/sign/")
            payload = page.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self):
            match = re.fullmatch(r"/sign/([a-f0-9-]{36})", self.path)
            if not match:
                self.send_error(404)
                return
            if self.client_address[0] not in {"127.0.0.1", "::1"}:
                self.send_error(403)
                return
            if self.headers.get_content_type() != "application/x-www-form-urlencoded":
                self.send_error(415)
                return
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 4096:
                self.send_error(413)
                return
            fields = parse_qs(self.rfile.read(length).decode("utf-8", errors="replace"))
            try:
                signed = sign_document(match.group(1), typed_name=fields.get("typed_name", [""])[0],
                                       consent=fields.get("consent", [""])[0] == "yes", data_dir=root)
            except CustomerError as exc:
                payload = ("<!doctype html><meta charset=utf-8><title>Unable to sign</title><p>" +
                           html.escape(str(exc)) + "</p>").encode("utf-8")
                self.send_response(400)
            else:
                payload = ("<!doctype html><meta charset=utf-8><title>Signed</title><main><h1>Document signed</h1><p>Your signed PDF and audit record were saved locally.</p><p>" +
                           html.escape(Path(signed["pdf_path"]).name) + "</p></main>").encode("utf-8")
                self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *_args):
            pass

    return ThreadingHTTPServer((host, port), SignaturePageHandler)
