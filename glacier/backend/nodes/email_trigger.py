"""IMAP polling trigger; the poller supplies one new message per durable run."""

import json


def run(ctx):
    trigger = ctx.get("trigger") or {}
    if trigger.get("type") != "email" or not isinstance(trigger.get("body"), dict):
        raise ValueError("This step starts when a new email arrives")
    return {"state": "done", "output": json.dumps(trigger["body"], ensure_ascii=False), "exit_code": 0}


NODE = {"catalog": {"type": "email_trigger", "label": "When an email arrives",
    "description": "Poll an IMAP mailbox over TLS and start once for each new matching message.",
    "fields": [
        {"key": "host", "label": "IMAP server", "placeholder": "imap.gmail.com", "default": ""},
        {"key": "port", "label": "IMAP port", "default": "993", "optional": True},
        {"key": "user", "label": "Email account", "placeholder": "you@example.com", "default": ""},
        {"key": "password", "label": "App password from Settings > Secrets", "placeholder": "{secret:EMAIL_APP_PASSWORD}", "default": ""},
        {"key": "folder", "label": "Mailbox", "placeholder": "INBOX", "default": "INBOX", "optional": True},
        {"key": "search", "label": "Only match", "placeholder": "UNSEEN or FROM name@example.com", "default": "UNSEEN"},
        {"key": "limit", "label": "Maximum messages per check", "default": "10", "optional": True},
    ], "branches": None, "worker": True}, "run": run}
