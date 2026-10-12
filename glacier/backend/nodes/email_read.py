"""Read message summaries from IMAP over TLS without changing mailbox state."""

from email import policy
from email.parser import BytesParser
import imaplib
import json
import re
import ssl

import secrets_store
import audit_log
import store


def _failed(message):
    return {"state": "failed", "output": secrets_store.redact(f"error: {message}"), "exit_code": 1}


def _search(value):
    text = str(value or "UNSEEN").strip()
    if text.upper() in {"ALL", "UNSEEN", "SEEN", "FLAGGED"}:
        return text.upper()
    match = re.fullmatch(r'(FROM|TO|SUBJECT)\s+(.{1,200})', text, re.I)
    if not match or any(char in match.group(2) for char in "\r\n"):
        raise ValueError("Search by ALL, UNSEEN, SEEN, FLAGGED, or FROM/TO/SUBJECT followed by text")
    term = match.group(2).replace('"', '').replace("\\", "\\\\")
    return f'{match.group(1).upper()} "{term}"'


def _body(message):
    part = message.get_body(preferencelist=("plain",)) if message.is_multipart() else message
    if part is None or part.get_content_type() != "text/plain":
        return ""
    try:
        return str(part.get_content())[:4000]
    except (LookupError, UnicodeError, TypeError):
        return ""


def run(ctx):
    config = ctx.get("config") or {}
    try:
        host = str(config.get("host") or "").strip()
        if not host or any(char in host for char in "\r\n/@"):
            raise ValueError("Enter the IMAP server from your email provider")
        port = max(1, min(65535, int(config.get("port") or 993)))
        timeout = max(5, min(120, int(config.get("timeout") or 30)))
        user = secrets_store.resolve(str(config.get("user") or ""))
        password = secrets_store.resolve(str(config.get("password") or ""))
        if not user or not password:
            raise ValueError("Add the email account name and save its app password in Settings > Secrets")
        folder = str(config.get("folder") or "INBOX")
        if not folder or any(char in folder for char in "\r\n"):
            raise ValueError("Enter a mailbox name such as INBOX")
        query = _search(config.get("search"))
        limit = max(1, min(25, int(config.get("limit") or 10)))
        messages = []
        client = imaplib.IMAP4_SSL(host, port, ssl_context=ssl.create_default_context(), timeout=timeout)
        try:
            client.login(user, password)
            status, _ = client.select(folder, readonly=True)
            if status != "OK":
                raise ValueError("The mailbox could not be opened")
            status, rows = client.search(None, query)
            if status != "OK":
                raise ValueError("The email search did not complete")
            ids = (rows[0].split() if rows else [])[-limit:]
            for msg_id in ids:
                status, parts = client.fetch(msg_id, "(RFC822)")
                if status != "OK":
                    continue
                raw = next((part[1] for part in parts if isinstance(part, tuple) and isinstance(part[1], bytes)), None)
                if raw is None:
                    continue
                message = BytesParser(policy=policy.default).parsebytes(raw)
                messages.append({"message_id": str(message.get("Message-ID", "")),
                    "from": str(message.get("From", "")), "to": str(message.get("To", "")),
                    "subject": str(message.get("Subject", "")), "date": str(message.get("Date", "")),
                    "body": _body(message)})
                if len(json.dumps(messages, ensure_ascii=False)) > 18_000:
                    messages.pop()
                    break
        finally:
            try:
                client.logout()
            except (OSError, imaplib.IMAP4.error):
                pass
        run_record = store.get_run(ctx.get("run_id", "")) or {"author": "owner"}
        audit_log.record("outbound.email_read", who=run_record.get("author", "owner"),
            what={"env_id": ctx.get("env_id", ""), "run_id": ctx.get("run_id", ""),
                  "node_id": ctx.get("node_id", ""), "host": host, "search": query, "count": len(messages)})
        return {"state": "done", "output": json.dumps(messages, ensure_ascii=False), "exit_code": 0}
    except (OSError, ValueError, TypeError, imaplib.IMAP4.error) as exc:
        return _failed(str(exc) or "Glacier could not search this mailbox")


NODE = {"catalog": {"type": "email_read", "label": "Search email",
    "description": "Find and read recent messages from your IMAP mailbox without marking them as read.",
    "fields": [
        {"key": "host", "label": "IMAP server", "placeholder": "imap.gmail.com", "default": ""},
        {"key": "port", "label": "IMAP port", "default": "993", "optional": True},
        {"key": "user", "label": "Email account", "placeholder": "you@example.com", "default": ""},
        {"key": "password", "label": "App password from Settings > Secrets", "placeholder": "{secret:EMAIL_APP_PASSWORD}", "default": ""},
        {"key": "folder", "label": "Mailbox", "placeholder": "INBOX", "default": "INBOX", "optional": True},
        {"key": "search", "label": "Search", "placeholder": "UNSEEN or FROM name@example.com", "default": "UNSEEN"},
        {"key": "limit", "label": "Maximum messages", "default": "10", "optional": True},
        {"key": "timeout", "label": "Time limit in seconds", "default": "30", "optional": True},
        {"key": "retries", "label": "Retries if it fails", "default": "0", "optional": True},
    ], "branches": None, "worker": True, "retry_safe": True}, "run": run}
