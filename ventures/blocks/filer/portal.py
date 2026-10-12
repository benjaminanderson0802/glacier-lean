from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import subprocess
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse

_RUNNER = Path(__file__).with_name("runner.mjs")
_SESSION_CACHE: dict[str, dict[str, Any]] = {}


def _default_evidence_dir() -> Path:
    return Path(os.environ.get("GLACIER_HOME", Path.home() / ".glacier")) / "ventures" / "filer"


def _validate_url(auth: dict[str, Any]) -> str:
    base_url = str(auth.get("base_url") or "").rstrip("/")
    parsed = urlparse(base_url)
    if not parsed.hostname or parsed.scheme not in {"http", "https"}:
        raise ValueError("auth.base_url must be an HTTP(S) portal URL")
    allowed = {"localhost", "127.0.0.1", "::1"}
    allowed.update(str(domain).lower() for domain in auth.get("allowed_domains", []))
    if parsed.hostname.lower() not in allowed:
        raise ValueError("portal host must be localhost or explicitly listed in auth.allowed_domains")
    if parsed.scheme == "http" and parsed.hostname.lower() not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("non-local portal URLs must use HTTPS")
    return base_url


def _run_browser(payload: dict[str, Any]) -> dict[str, Any]:
    node = os.environ.get("NODE", "node")
    try:
        result = subprocess.run([node, str(_RUNNER)], input=json.dumps(payload), text=True, capture_output=True, timeout=90, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"Playwright portal operation failed: {exc}") from exc
    if result.returncode:
        # Do not include browser input or credentials in exception output.
        raise RuntimeError(f"Playwright portal operation failed: {result.stderr[-500:].strip()}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Playwright portal operation returned invalid output") from exc


def prepare(portal_id: str, fields: dict[str, Any], auth: dict[str, Any], *, evidence_dir: str | Path | None = None) -> dict[str, Any]:
    """Login and fill a portal's multi-step form, save a screenshot, and stop before submission."""
    if not portal_id or not isinstance(fields, dict) or not fields:
        raise ValueError("portal_id and non-empty fields are required")
    if not auth.get("username") or not auth.get("password"):
        raise ValueError("portal login credentials are required for preparation")
    base_url = _validate_url(auth)
    destination = Path(evidence_dir) if evidence_dir else _default_evidence_dir()
    destination.mkdir(parents=True, exist_ok=True)
    idempotency_key = uuid.uuid4().hex
    screenshot = destination / f"draft-{idempotency_key}.png"
    result = _run_browser({"operation": "prepare", "baseUrl": base_url, "username": str(auth["username"]), "password": str(auth["password"]), "fields": fields, "screenshot": str(screenshot)})
    _SESSION_CACHE[idempotency_key] = result["storageState"]
    return {
        "status": "prepared",
        "portal_id": portal_id,
        "base_url": base_url,
        "fields": fields,
        "idempotency_key": idempotency_key,
        "screenshot": str(screenshot),
        "review_url": f"{base_url}/review",
    }


@contextmanager
def _database(path: Path) -> Iterator[sqlite3.Connection]:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=60, isolation_level=None)
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("CREATE TABLE IF NOT EXISTS confirmations (idempotency_key TEXT PRIMARY KEY, approval_id TEXT NOT NULL, confirmation_json TEXT NOT NULL)")
        connection.execute("BEGIN IMMEDIATE")
        yield connection
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()


def submit(draft: dict[str, Any], approval_id: str, *, evidence_dir: str | Path | None = None) -> dict[str, Any]:
    """Submit a prepared draft only with an approval id; save and replay its confirmation idempotently."""
    if not approval_id or not str(approval_id).strip():
        raise ValueError("approval_id is required before portal submission")
    if not isinstance(draft, dict) or draft.get("status") != "prepared":
        raise ValueError("a prepared portal draft is required")
    key = str(draft.get("idempotency_key") or "")
    if not re.fullmatch(r"[a-f0-9]{32}", key):
        raise ValueError("draft has no valid idempotency key")
    required = {"portal_id", "base_url", "fields"}
    if not required.issubset(draft):
        raise ValueError("draft is missing portal fields")
    destination = Path(evidence_dir) if evidence_dir else _default_evidence_dir()
    database = destination / "idempotency.sqlite3"
    with _database(database) as connection:
        saved = connection.execute("SELECT confirmation_json FROM confirmations WHERE idempotency_key=?", (key,)).fetchone()
        if saved:
            return json.loads(saved[0])
        session_state = _SESSION_CACHE.get(key)
        if session_state is None:
            raise ValueError("the prepared login session expired; prepare the portal draft again before approval")
        screenshot = destination / f"confirmation-{key}.png"
        pdf = destination / f"confirmation-{key}.pdf"
        result = _run_browser({"operation": "submit", "baseUrl": draft["base_url"], "storageState": session_state, "fields": draft["fields"], "screenshot": str(screenshot), "pdf": str(pdf)})
        body = result.get("text", "")
        reference = re.search(r"(?:confirmation(?:\s+number)?|reference|receipt)\s*(?:number|#|:)?\s*([A-Za-z0-9_-]+)", body, re.I)
        confirmation = {
            "status": "submitted",
            "portal_id": draft["portal_id"],
            "idempotency_key": key,
            "approval_id": str(approval_id),
            "reference": reference.group(1) if reference else body[:300].strip(),
            "screenshot": str(screenshot),
            "pdf": str(pdf),
            "fields_sha256": hashlib.sha256(json.dumps(draft["fields"], sort_keys=True, default=str).encode()).hexdigest(),
        }
        connection.execute("INSERT INTO confirmations(idempotency_key, approval_id, confirmation_json) VALUES (?, ?, ?)", (key, str(approval_id), json.dumps(confirmation)))
        _SESSION_CACHE.pop(key, None)
        return confirmation
