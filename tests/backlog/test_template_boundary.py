"""Independent real-backend checks for template import provenance.

Acceptance, written before implementation:
* a reviewed, unchanged bundle remains installable and can be submitted to the import API;
* a changed bundle is visibly unavailable;
* an imported flow is pending and absent from the executable gallery until approval;
* changing reviewed commands or adding capabilities before approval cannot make the
  changed proposal executable, traversal cannot select another proposal, and unknown
  step capabilities are rejected;
* retain each exact HTTP status/body and the corresponding audit references.

This is an evaluator check only. It starts the actual FastAPI backend with a disposable
GLACIER_HOME. The bundled template directory is copied into that disposable fixture so
digest tampering never writes to the checkout.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import time

import httpx
ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "glacier" / "backend"
TOKEN = "template-boundary-test-token"
EVIDENCE = ROOT / "evidence" / "backlog" / "B-TEMPLATE-BOUNDARY"


def _port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class _Backend:
    def __init__(self, home: Path, templates: Path):
        self.home = home
        self.port = _port()
        self.url = f"http://127.0.0.1:{self.port}"
        self.log_path = home / "backend.log"
        self.log = self.log_path.open("w", encoding="utf-8")
        self.process: subprocess.Popen | None = None
        shim = home / "python-shim"
        shim.mkdir()
        (shim / "sitecustomize.py").write_text(
            "import os, sys\n"
            f"sys.path.insert(0, {str(BACKEND)!r})\n"
            "import template_registry\n"
            "from pathlib import Path\n"
            "template_registry.BUNDLED_DIR = Path(os.environ['TEMPLATE_BOUNDARY_BUNDLES'])\n",
            encoding="utf-8",
        )
        self.env = dict(os.environ)
        self.env.update({
            "GLACIER_HOME": str(home / "state"),
            "GLACIER_TOKEN": TOKEN,
            "GLACIER_OLLAMA_URL": "http://127.0.0.1:9",
            "CODEX_BIN": str(BACKEND / "tests" / "fake_codex.py"),
            "TEMPLATE_BOUNDARY_BUNDLES": str(templates),
            "PYTHONPATH": os.pathsep.join([str(shim), str(BACKEND), self.env.get("PYTHONPATH", "")]),
            "GIT_AUTHOR_NAME": "Glacier Template Boundary Test",
            "GIT_AUTHOR_EMAIL": "template-boundary@localhost",
            "GIT_COMMITTER_NAME": "Glacier Template Boundary Test",
            "GIT_COMMITTER_EMAIL": "template-boundary@localhost",
        })

    def start(self) -> None:
        self.process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(self.port)],
            cwd=BACKEND, env=self.env, stdout=self.log, stderr=subprocess.STDOUT,
            start_new_session=(os.name != "nt"),
        )
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline and self.process.poll() is None:
            try:
                response = httpx.get(self.url + "/api/templates", headers=self.headers, timeout=2)
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.1)
        self.log.flush()
        detail = self.log_path.read_text(encoding="utf-8", errors="replace")
        raise RuntimeError(f"Disposable Glacier backend did not start:\n{detail}")

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {TOKEN}"}

    def request(self, method: str, path: str, *, json_body=None) -> httpx.Response:
        return httpx.request(method, self.url + path, headers=self.headers, json=json_body, timeout=30)

    def stop(self) -> None:
        if self.process and self.process.poll() is None:
            if os.name == "nt":
                self.process.terminate()
            else:
                os.killpg(self.process.pid, signal.SIGTERM)
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                if os.name == "nt":
                    self.process.kill()
                else:
                    os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait(timeout=5)
        if not self.log.closed:
            self.log.close()


def _flow(step_type: str = "command", flow_id: str = "boundary-fixture") -> dict:
    config = {"cmd": "printf reviewed"} if step_type == "command" else {"to": "local-review@localhost", "subject": "fixture", "body": "fixture"}
    return {
        "id": flow_id,
        "name": "Boundary fixture",
        "goal": "Import a synthetic flow without running it.",
        "acceptance": [{"kind": "command", "cmd": "test -n '{prev_output}'"}],
        "nodes": [{"id": "step", "type": step_type, "config": config, "position": {"x": 0, "y": 0}}],
        "edges": [],
    }


def _portable(flow: dict) -> str:
    return json.dumps({"glacier_flow": 1, "flow": flow}, ensure_ascii=False)


def _capture(records: list[dict], name: str, response: httpx.Response) -> dict:
    try:
        body = response.json()
    except ValueError:
        body = response.text
    record = {"case": name, "method": response.request.method, "url": str(response.request.url),
              "status": response.status_code, "body": body}
    records.append(record)
    return record


def test_template_provenance_and_approval_boundary_on_real_backend(tmp_path):
    bundle_copy = tmp_path / "bundles"
    shutil.copytree(ROOT / "templates", bundle_copy)
    backend = _Backend(tmp_path, bundle_copy)
    backend.start()
    records: list[dict] = []
    checks: dict[str, object] = {}
    try:
        listed = _capture(records, "unchanged_manifest", backend.request("GET", "/api/templates"))
        assert listed["status"] == 200
        unchanged = next(item for item in listed["body"] if item["id"] == "tpl-daily-report")
        unchanged_template = unchanged["template"]
        checks["unchanged_reviewed_bundle_installable"] = unchanged["review_status"] == "reviewed" and unchanged["installable"] is True

        manifest = json.loads((bundle_copy / "manifest" / "MANIFEST.json").read_text(encoding="utf-8"))
        entry = next(item for item in manifest["templates"] if item["id"] == "tpl-daily-report")
        tampered_path = bundle_copy / entry["file"]
        tampered = json.loads(tampered_path.read_text(encoding="utf-8"))
        tampered["name"] = "Modified after manifest review"
        tampered_path.write_text(json.dumps(tampered), encoding="utf-8")
        after_tamper = _capture(records, "tampered_manifest", backend.request("GET", "/api/templates"))
        tampered_entry = next(item for item in after_tamper["body"] if item["id"] == "tpl-daily-report")
        checks["tampered_bundle_unavailable"] = (
            tampered_entry["review_status"] == "changed since review"
            and tampered_entry["installable"] is False
            and "template" not in tampered_entry
        )

        # Restore only the disposable bundle so the import cases are independent of the digest case.
        shutil.copy2(ROOT / "templates" / entry["file"], tampered_path)
        clean = _capture(records, "review_import", backend.request(
            "POST", "/api/templates/import", json_body={"file": _portable(unchanged_template)},
        ))
        proposal_id = clean["body"].get("id")
        checks["import_is_pending_and_commands_are_recorded"] = (
            clean["status"] == 200 and clean["body"].get("accepted") is True
            and clean["body"].get("status") == "pending"
            and clean["body"].get("commands_for_review") == ["date -Is"]
        )
        before_approval = _capture(records, "pending_not_in_gallery", backend.request("GET", "/api/templates"))
        checks["pending_template_not_installable"] = not any(
            item.get("id") == clean["body"].get("template_id") for item in before_approval["body"]
        )

        if proposal_id:
            pending_file = tmp_path / "state" / "templates" / "pending" / f"{proposal_id}.json"
            pending = json.loads(pending_file.read_text(encoding="utf-8"))
            command_node = next(node for node in pending["template"]["nodes"] if "cmd" in node.get("config", {}))
            command_node["config"]["cmd"] = "curl https://example.invalid"
            # Keep the review snapshot unchanged to simulate a proposal replaced after review.
            pending_file.write_text(json.dumps(pending), encoding="utf-8")
            replacement = _capture(records, "approve_replaced_command", backend.request(
                "POST", f"/api/templates/import/{proposal_id}/approve",
            ))
            checks["replaced_command_refused"] = replacement["status"] != 200 or replacement["body"].get("status") != "approved"
            after_replacement = _capture(records, "gallery_after_replaced_command", backend.request("GET", "/api/templates"))
            checks["replaced_command_not_executable"] = not any(
                item.get("id") == clean["body"].get("template_id") for item in after_replacement["body"]
            )

        capability_flow = json.loads(json.dumps(unchanged_template))
        capability_flow["id"] = "tpl-capability-fixture"
        capability_review = _capture(records, "review_before_capability_injection", backend.request(
            "POST", "/api/templates/import", json_body={"file": _portable(capability_flow)},
        ))
        capability_id = capability_review["body"].get("id")
        checks["capability_base_reviewed"] = capability_review["status"] == 200 and capability_review["body"].get("accepted") is True
        if capability_id:
            pending_file = tmp_path / "state" / "templates" / "pending" / f"{capability_id}.json"
            pending = json.loads(pending_file.read_text(encoding="utf-8"))
            pending["template"]["nodes"].append({
                "id": "unreviewed-send", "type": "email_send",
                "config": {"to": "local-review@localhost", "subject": "fixture", "body": "fixture"},
                "position": {"x": 1040, "y": 0},
            })
            pending_file.write_text(json.dumps(pending), encoding="utf-8")
            injected = _capture(records, "approve_added_capability", backend.request(
                "POST", f"/api/templates/import/{capability_id}/approve",
            ))
            checks["replaced_capability_refused"] = injected["status"] != 200 or injected["body"].get("status") != "approved"
            injected_gallery = _capture(records, "gallery_after_added_capability", backend.request("GET", "/api/templates"))
            checks["added_capability_not_executable"] = not any(
                item.get("id") == capability_review["body"].get("template_id") for item in injected_gallery["body"]
            )

        capability = _capture(records, "unreviewed_capability_import", backend.request(
            "POST", "/api/templates/import", json_body={"file": _portable(_flow("not_a_registered_capability", "unknown-capability-fixture"))},
        ))
        checks["unknown_capability_rejected"] = capability["status"] == 200 and capability["body"].get("accepted") is False

        # A known side-effect capability still has to remain pending until the owner approves it.
        email = _capture(records, "side_effect_capability_pending", backend.request(
            "POST", "/api/templates/import", json_body={"file": _portable(_flow("email_send", "side-effect-fixture"))},
        ))
        if email["body"].get("accepted") is True:
            email_gallery = _capture(records, "side_effect_capability_gallery_before_approval", backend.request("GET", "/api/templates"))
            checks["side_effect_capability_pending_not_listed"] = not any(
                item.get("id") == email["body"].get("template_id") for item in email_gallery["body"]
            ) and email["body"].get("status") == "pending"
        else:
            checks["side_effect_capability_pending_not_listed"] = True

        traversal = _capture(records, "traversal_approval_id", backend.request(
            "POST", "/api/templates/import/%2e%2e%2foutside/approve",
        ))
        checks["traversal_rejected"] = traversal["status"] == 404
    finally:
        backend.stop()

    audit_path = tmp_path / "state" / "audit.sqlite"
    audit = []
    if audit_path.exists():
        with sqlite3.connect(audit_path) as connection:
            connection.row_factory = sqlite3.Row
            audit = [dict(row) for row in connection.execute(
                "SELECT id, event_type, who, what, happened_at FROM glacier_audit ORDER BY id"
            )]
        for row in audit:
            row["what"] = json.loads(row["what"])

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    result = {"fixture_kind": "real FastAPI backend; synthetic flows; disposable GLACIER_HOME and copied template bundle",
              "checks": checks, "api": records, "audit": audit}
    (EVIDENCE / "template-boundary-api.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    failures = [name for name, passed in checks.items() if passed is not True]
    assert not failures, f"template boundary acceptance checks failed: {', '.join(failures)}"
