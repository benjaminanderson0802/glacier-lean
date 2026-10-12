"""Save local email drafts or send through an owner-configured SMTP server."""

from email.message import EmailMessage
from email.utils import parseaddr
import os
from pathlib import Path
import re
import smtplib
import ssl

import secrets_store
import audit_log
import store


def _failed(message):
    return {"state": "failed", "output": secrets_store.redact(f"error: {message}"), "exit_code": 1}


def _fill(value, ctx):
    previous = (ctx.get("prev") or {}).get("output") or ""
    return str(value or "").replace("{env}", str(ctx.get("env_id") or "")).replace(
        "{run}", str(ctx.get("run_id") or "")).replace("{prev_output}", str(previous)[-8000:])


def _address(value, label):
    text = str(value or "").strip()
    name, address = parseaddr(text)
    if not address or "@" not in address or any(char in text for char in "\r\n"):
        raise ValueError(f"Enter a valid {label} email address")
    return text


def run(ctx):
    config = ctx.get("config") or {}
    try:
        sender = _address(config.get("from"), "From")
        recipient = _address(_fill(config.get("to"), ctx), "To")
        subject = _fill(config.get("subject"), ctx).strip()
        body = _fill(config.get("body"), ctx)
        if not subject or len(subject) > 500 or not body:
            raise ValueError("Add a subject and message")
        message = EmailMessage()
        message["From"] = sender
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)

        draft_only = str(config.get("draft_only", "Yes")).strip().lower() not in {"no", "false", "0"}
        if draft_only:
            workspace = Path(ctx.get("workspace") or Path(ctx["home"]) / "workspaces" / ctx.get("env_id", "default")).resolve()
            drafts = (workspace / "drafts").resolve()
            if workspace not in drafts.parents:
                raise ValueError("The draft folder must stay inside this flow's folder")
            drafts.mkdir(parents=True, exist_ok=True)
            safe_node = re.sub(r"[^A-Za-z0-9_-]", "_", str(ctx.get("node_id", "email")))[:80]
            safe_run = re.sub(r"[^A-Za-z0-9_-]", "_", str(ctx.get("run_id", "draft")))[:80]
            name = f"{safe_node or 'email'}-{safe_run or 'draft'}.eml"
            target = drafts / name
            target.write_bytes(message.as_bytes())
            run_record = store.get_run(ctx.get("run_id", "")) or {"author": "owner"}
            audit_log.record("email.draft_saved", who=run_record.get("author", "owner"),
                what={"env_id": ctx.get("env_id", ""), "run_id": ctx.get("run_id", ""),
                      "node_id": ctx.get("node_id", ""), "path": f"drafts/{name}"})
            return {"state": "done", "output": f"drafts/{name}", "exit_code": 0}

        if not ctx.get("approved_by_human"):
            raise ValueError("Place an Approval step immediately before sending and approve this message first")
        host = str(config.get("host") or "").strip()
        if not host or any(char in host for char in "\r\n/@"):
            raise ValueError("Enter the SMTP server from your email provider")
        port = max(1, min(65535, int(config.get("port") or 587)))
        timeout = max(5, min(120, int(config.get("timeout") or 30)))
        user = secrets_store.resolve(str(config.get("user") or ""))
        password = secrets_store.resolve(str(config.get("password") or ""))
        if not user or not password:
            raise ValueError("Add the email account name and save its app password in Settings > Secrets")
        with smtplib.SMTP(host, port, timeout=timeout) as client:
            client.ehlo()
            client.starttls(context=ssl.create_default_context())
            client.ehlo()
            client.login(user, password)
            client.send_message(message)
        run_record = store.get_run(ctx.get("run_id", "")) or {"author": "owner"}
        audit_log.record("outbound.email_sent", who=run_record.get("author", "owner"),
            what={"env_id": ctx.get("env_id", ""), "run_id": ctx.get("run_id", ""),
                  "node_id": ctx.get("node_id", ""), "host": host, "to": recipient})
        return {"state": "done", "output": f"Email sent to {recipient}", "exit_code": 0}
    except (OSError, ValueError, TypeError, smtplib.SMTPException) as exc:
        return _failed(str(exc) or "Glacier could not send this email")


NODE = {"catalog": {"type": "email_send", "label": "Write or send email",
    "description": "Save a draft on this computer or send through your SMTP account after approval.",
    "fields": [
        {"key": "draft_only", "label": "Keep as a draft", "default": "Yes", "options": ["Yes", "No"]},
        {"key": "host", "label": "SMTP server", "placeholder": "smtp.gmail.com", "default": "", "optional": True},
        {"key": "port", "label": "SMTP port", "default": "587", "optional": True},
        {"key": "user", "label": "Email account", "placeholder": "you@example.com", "default": "", "optional": True},
        {"key": "password", "label": "App password from Settings > Secrets", "placeholder": "{secret:EMAIL_APP_PASSWORD}", "default": "", "optional": True},
        {"key": "from", "label": "From", "placeholder": "you@example.com", "default": ""},
        {"key": "to", "label": "To", "placeholder": "person@example.com", "default": ""},
        {"key": "subject", "label": "Subject", "placeholder": "Hello {env}", "default": ""},
        {"key": "body", "label": "Message", "placeholder": "Write your message here", "default": "", "multiline": True},
        {"key": "timeout", "label": "Time limit in seconds", "default": "30", "optional": True},
    ], "branches": None, "worker": True, "changing_methods": ["SMTP SEND"]}, "run": run}
