"""Template manifest, provenance checks, and owner reviewed community proposals."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sys
import uuid

import portable
import verify


BACKEND_DIR = Path(__file__).resolve().parent
BUNDLED_DIR = BACKEND_DIR.parents[1] / "templates"
RISKY_COMMANDS = (
    (re.compile(r"\bcurl\b", re.IGNORECASE), "curl"),
    (re.compile(r"\bwget\b", re.IGNORECASE), "wget"),
    (re.compile(r"\bnc\b", re.IGNORECASE), "nc"),
    (re.compile(r"\bssh\b", re.IGNORECASE), "ssh"),
    (re.compile(r"\bscp\b", re.IGNORECASE), "scp"),
    (re.compile(r"\brm\s+-rf\b", re.IGNORECASE), "rm -rf"),
    (re.compile(r"\bsudo\b", re.IGNORECASE), "sudo"),
)


def _contains_paid_route(value) -> bool:
    if isinstance(value, dict):
        return ("paid" in value and value["paid"] is not False) or any(_contains_paid_route(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_paid_route(item) for item in value)
    return False


def update_manifest() -> dict:
    """Recompute the bundled template manifest hashes for maintainers."""
    entries = []
    for path in sorted(BUNDLED_DIR.glob("*.json")):
        if path.name == "MANIFEST.json":
            continue
        flow = json.loads(path.read_text(encoding="utf-8"))
        entries.append({
            "id": flow["id"], "file": path.name, "name": flow["name"],
            "description": flow.get("description", flow["name"]),
            "author": "Glacier", "license": "Apache-2.0",
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "reviewed_by": "Glacier maintainers", "reviewed_on": "2026-10-07",
        })
    result = {"templates": entries}
    (BUNDLED_DIR / "MANIFEST.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def _manifest() -> list[dict]:
    try:
        value = json.loads((BUNDLED_DIR / "MANIFEST.json").read_text(encoding="utf-8"))
        return value.get("templates", [])
    except (OSError, ValueError, AttributeError):
        return []


def list_templates() -> list[dict]:
    result = []
    for entry in _manifest():
        path = BUNDLED_DIR / entry.get("file", "")
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""
        changed = actual != entry.get("sha256")
        item = dict(entry)
        item.update({"review_status": "changed since review" if changed else "reviewed", "installable": not changed})
        if not changed:
            item["template"] = json.loads(path.read_text(encoding="utf-8"))
        result.append(item)
    approved_dir = _home() / "templates" / "approved"
    if approved_dir.is_dir():
        for path in sorted(approved_dir.glob("*.json")):
            proposal = json.loads(path.read_text(encoding="utf-8"))
            item = proposal["template"]
            result.append({"id": item["id"], "name": item.get("name", item["id"]), "description": item.get("description", ""),
                           "author": proposal.get("author", "Community contributor"), "license": item.get("license", ""),
                           "review_status": "approved", "installable": True, "template": item})
    return result


def _home() -> Path:
    return Path(os.environ.get("GLACIER_HOME", "data")).resolve()


def review_import(text: str) -> dict:
    findings: list[str] = []
    try:
        flow = portable.import_flow(text, set())
    except (TypeError, ValueError) as exc:
        return {"accepted": False, "review": [str(exc)]}

    try:
        verify.validate(flow.get("acceptance"))
    except (TypeError, ValueError) as exc:
        findings.append(f"Acceptance checks are invalid: {exc}")
    if flow.get("goal") and not flow.get("acceptance"):
        findings.append("Every goal needs at least one acceptance check.")

    nodes = flow.get("nodes", [])
    for node in nodes:
        config = node.get("config") or {}
        node_id = node.get("id", "unnamed node")
        if not isinstance(config, dict):
            findings.append(f"Node {node_id} settings must be an object.")
            continue
        if node.get("type") == "command":
            command = str(config.get("cmd", ""))
            for pattern, match in RISKY_COMMANDS:
                if pattern.search(command):
                    findings.append(f"Node {node_id} uses a flagged command ({match}).")
        if re.search(r"\{secret:[^}]*\}", json.dumps(config, ensure_ascii=False)):
            findings.append(f"Node {node_id} contains a secret placeholder ({'{secret:}'}).")
        if node.get("type") == "codex":
            config["sandbox"] = "read-only"

        if config.get("engine") == "gateway" or _contains_paid_route(config.get("routes", [])):
            findings.append(f"Node {node_id} selects a paid model route.")

    if findings:
        return {"accepted": False, "review": findings}

    proposal_id = uuid.uuid4().hex
    proposal = {"id": proposal_id, "status": "pending", "author": flow.get("author", "Community contributor"), "template": flow}
    pending = _home() / "templates" / "pending"
    pending.mkdir(parents=True, exist_ok=True)
    (pending / f"{proposal_id}.json").write_text(json.dumps(proposal, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"accepted": True, "review": [], "id": proposal_id, "status": "pending"}


def approve_import(proposal_id: str) -> dict:
    pending_path = _home() / "templates" / "pending" / f"{proposal_id}.json"
    if not pending_path.is_file():
        raise FileNotFoundError(proposal_id)
    proposal = json.loads(pending_path.read_text(encoding="utf-8"))
    proposal["status"] = "approved"
    approved = _home() / "templates" / "approved"
    approved.mkdir(parents=True, exist_ok=True)
    destination = approved / f"{proposal_id}.json"
    destination.write_text(json.dumps(proposal, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    pending_path.unlink()
    return {"id": proposal_id, "status": "approved"}


if __name__ == "__main__" and sys.argv[1:] == ["--update-manifest"]:
    update_manifest()
