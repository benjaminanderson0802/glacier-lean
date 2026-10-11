"""Frozen external evaluator for reviewed community-template approvals.

Acceptance (written first): approval is allowed only when the template's command and
capability content still matches the immutable content shown during review. An unchanged
proposal approves and becomes installable; changed commands/capabilities stay pending and
non-installable. Encoded traversal is rejected, unknown step types are refused, and a
side-effect template remains pending and absent from the gallery until explicit approval.

The real API runs in a child process with a disposable GLACIER_HOME. Proposal tampering
models replacement of persisted state between review and approval; all interactions that
decide or expose approval happen through the public API. The screen mock currently does
not implement template import/approval, so a separate mock probe records that boundary.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

import httpx
import pytest


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "glacier" / "backend"
MOCK = ROOT / "glacier" / "web" / "mock" / "mock_server.mjs"
EVIDENCE = ROOT / "evidence" / "backlog2" / "C-TEMPLATE-APPROVAL-TESTER"
TOKEN = "template-approval-snapshot-test-token"


def _port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class _Server:
    def __init__(self, home: Path):
        self.home = home
        self.port = _port()
        self.url = f"http://127.0.0.1:{self.port}"
        self.log_path = home / "backend.log"
        self.log = self.log_path.open("w", encoding="utf-8")
        env = dict(os.environ)
        env.update({
            "GLACIER_HOME": str(home / "state"),
            "GLACIER_TOKEN": TOKEN,
            "GLACIER_OLLAMA_URL": "http://127.0.0.1:9",
            "CODEX_BIN": str(BACKEND / "tests" / "fake_codex.py"),
            "GIT_AUTHOR_NAME": "Template Approval Snapshot Test",
            "GIT_AUTHOR_EMAIL": "template-approval@localhost",
            "GIT_COMMITTER_NAME": "Template Approval Snapshot Test",
            "GIT_COMMITTER_EMAIL": "template-approval@localhost",
        })
        self.process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(self.port)],
            cwd=BACKEND, env=env, stdout=self.log, stderr=subprocess.STDOUT,
            start_new_session=(os.name != "nt"),
        )
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline and self.process.poll() is None:
            try:
                if httpx.get(self.url + "/api/templates", headers=self.headers, timeout=2).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.1)
        else:
            self.log.flush()
            raise RuntimeError(f"Disposable backend failed to start:\n{self.log_path.read_text(encoding='utf-8')}")

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {TOKEN}"}

    def request(self, method: str, path: str, body=None) -> httpx.Response:
        return httpx.request(method, self.url + path, headers=self.headers, json=body, timeout=30)

    def stop(self) -> None:
        if self.process.poll() is None:
            if os.name == "nt":
                self.process.terminate()
            else:
                os.killpg(self.process.pid, signal.SIGTERM)
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self.log.close()


def _portable(flow: dict) -> str:
    return json.dumps({"glacier_flow": 1, "flow": flow}, ensure_ascii=False)


def _daily_flow() -> dict:
    return json.loads((ROOT / "templates" / "tpl-daily-report.json").read_text(encoding="utf-8"))


def _synthetic_flow(step_type: str, flow_id: str) -> dict:
    config = {"cmd": "printf reviewed"} if step_type == "command" else {
        "to": "fixture@localhost", "subject": "approval fixture", "body": "not sent",
    }
    return {
        "id": flow_id,
        "name": "Approval snapshot fixture",
        "goal": "Review an imported flow without running it.",
        "acceptance": [{"kind": "command", "cmd": "test -n '{prev_output}'"}],
        "nodes": [{"id": "step", "type": step_type, "config": config, "position": {"x": 0, "y": 0}}],
        "edges": [],
    }


def _record(records: list[dict], name: str, response: httpx.Response) -> dict:
    try:
        body = response.json()
    except ValueError:
        body = response.text
    if response.request.url.path == "/api/templates" and isinstance(body, list):
        body = [
            {key: item.get(key) for key in ("id", "review_status", "installable")}
            for item in body
        ]
    value = {"case": name, "method": response.request.method, "url": str(response.request.url),
             "status": response.status_code, "body": body}
    records.append(value)
    return value


def _gallery_contains(record: dict, template_id: str) -> bool:
    return any(item.get("id") == template_id and item.get("installable") is True for item in record["body"])


def test_template_approval_is_bound_to_reviewed_snapshot(tmp_path):
    server = _Server(tmp_path)
    checks: dict[str, bool] = {}
    records: list[dict] = []
    try:
        gallery = _record(records, "unchanged_bundle", server.request("GET", "/api/templates"))
        bundled = next(item for item in gallery["body"] if item["id"] == "tpl-daily-report")
        flow = _daily_flow()
        checks["unchanged_template_is_reviewed_and_installable"] = (
            bundled.get("review_status") == "reviewed" and bundled.get("installable") is True
        )

        clean = _record(records, "import_unchanged_template", server.request(
            "POST", "/api/templates/import", {"file": _portable(flow)},
        ))
        clean_id = clean["body"].get("id") if isinstance(clean["body"], dict) else None
        checks["unchanged_import_is_pending"] = (
            clean["status"] == 200 and clean["body"].get("accepted") is True
            and clean["body"].get("status") == "pending"
        )
        if clean_id:
            approval = _record(records, "approve_unchanged_template", server.request(
                "POST", f"/api/templates/import/{clean_id}/approve",
            ))
            checks["unchanged_reviewed_content_approves"] = (
                approval["status"] == 200 and approval["body"].get("status") == "approved"
            )
            after = _record(records, "gallery_after_unchanged_approval", server.request("GET", "/api/templates"))
            checks["unchanged_approved_template_is_installable"] = _gallery_contains(after, clean["body"].get("template_id", ""))
        else:
            checks["unchanged_reviewed_content_approves"] = False
            checks["unchanged_approved_template_is_installable"] = False

        command = _record(records, "review_before_command_change", server.request(
            "POST", "/api/templates/import", {"file": _portable(flow)},
        ))
        command_id = command["body"].get("id") if isinstance(command["body"], dict) else None
        if command_id:
            pending_path = tmp_path / "state" / "templates" / "pending" / f"{command_id}.json"
            proposal = json.loads(pending_path.read_text(encoding="utf-8"))
            node = next(n for n in proposal["template"]["nodes"] if "cmd" in n.get("config", {}))
            node["config"]["cmd"] = "curl https://example.invalid"
            pending_path.write_text(json.dumps(proposal), encoding="utf-8")
            changed = _record(records, "approve_changed_command", server.request(
                "POST", f"/api/templates/import/{command_id}/approve",
            ))
            checks["changed_command_approval_refused"] = changed["status"] != 200 or changed["body"].get("status") != "approved"
            after = _record(records, "gallery_after_changed_command", server.request("GET", "/api/templates"))
            checks["changed_command_remains_noninstallable"] = not _gallery_contains(after, command["body"].get("template_id", ""))
            checks["changed_command_proposal_remains_pending"] = pending_path.exists()
        else:
            checks.update({"changed_command_approval_refused": False,
                           "changed_command_remains_noninstallable": False,
                           "changed_command_proposal_remains_pending": False})

        capability_flow = json.loads(json.dumps(flow))
        capability_flow["id"] = "approval-capability-fixture"
        capability = _record(records, "review_before_capability_change", server.request(
            "POST", "/api/templates/import", {"file": _portable(capability_flow)},
        ))
        capability_id = capability["body"].get("id") if isinstance(capability["body"], dict) else None
        if capability_id:
            pending_path = tmp_path / "state" / "templates" / "pending" / f"{capability_id}.json"
            proposal = json.loads(pending_path.read_text(encoding="utf-8"))
            proposal["template"]["nodes"].append({
                "id": "unreviewed-send", "type": "email_send",
                "config": {"to": "fixture@localhost", "subject": "not sent", "body": "not sent"},
                "position": {"x": 500, "y": 0},
            })
            pending_path.write_text(json.dumps(proposal), encoding="utf-8")
            changed = _record(records, "approve_added_capability", server.request(
                "POST", f"/api/templates/import/{capability_id}/approve",
            ))
            checks["added_capability_approval_refused"] = changed["status"] != 200 or changed["body"].get("status") != "approved"
            after = _record(records, "gallery_after_added_capability", server.request("GET", "/api/templates"))
            checks["added_capability_remains_noninstallable"] = not _gallery_contains(after, capability["body"].get("template_id", ""))
            checks["added_capability_proposal_remains_pending"] = pending_path.exists()
        else:
            checks.update({"added_capability_approval_refused": False,
                           "added_capability_remains_noninstallable": False,
                           "added_capability_proposal_remains_pending": False})

        unknown = _record(records, "unknown_step_type", server.request(
            "POST", "/api/templates/import",
            {"file": _portable(_synthetic_flow("not_a_registered_capability", "unknown-step-fixture"))},
        ))
        checks["unknown_step_rejected"] = unknown["status"] == 200 and unknown["body"].get("accepted") is False

        side_effect = _record(records, "side_effect_import", server.request(
            "POST", "/api/templates/import",
            {"file": _portable(_synthetic_flow("email_send", "side-effect-fixture"))},
        ))
        side_effect_id = side_effect["body"].get("id") if isinstance(side_effect["body"], dict) else None
        if side_effect["body"].get("accepted") is True:
            before = _record(records, "side_effect_pending_gallery", server.request("GET", "/api/templates"))
            checks["side_effect_is_pending_and_not_installable"] = (
                side_effect["body"].get("status") == "pending"
                and not _gallery_contains(before, side_effect["body"].get("template_id", ""))
            )
            side_approval = _record(records, "explicitly_approve_side_effect_template", server.request(
                "POST", f"/api/templates/import/{side_effect_id}/approve",
            ))
            checks["side_effect_requires_explicit_approval"] = (
                side_approval["status"] == 200 and side_approval["body"].get("status") == "approved"
            )
        else:
            checks["side_effect_is_pending_and_not_installable"] = False
            checks["side_effect_requires_explicit_approval"] = False

        traversal = _record(records, "encoded_traversal", server.request(
            "POST", "/api/templates/import/%2e%2e%2foutside/approve",
        ))
        checks["encoded_traversal_rejected"] = traversal["status"] == 404
    finally:
        server.stop()

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    result = {
        "fixture_kind": "real FastAPI backend, synthetic proposals, disposable GLACIER_HOME",
        "checks": checks,
        "api": records,
    }
    (EVIDENCE / "template-approval-snapshot-api.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
    )
    failed = [name for name, passed in checks.items() if passed is not True]
    assert not failed, f"template approval snapshot checks failed: {', '.join(failed)}"


def test_current_screen_mock_exposes_template_gallery_but_not_import_api(tmp_path):
    """Probe the existing screen mock; approval API coverage belongs to the real backend."""
    if not (ROOT / "glacier" / "web" / "node_modules" / "ws" / "package.json").is_file():
        pytest.skip("screen mock dependency ws is not installed in this worktree")
    port = _port()
    log_path = tmp_path / "mock.log"
    log = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        ["node", str(MOCK), str(port)], cwd=ROOT / "glacier" / "web",
        stdout=log, stderr=subprocess.STDOUT, start_new_session=(os.name != "nt"),
    )
    url = f"http://127.0.0.1:{port}"
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline and process.poll() is None:
            try:
                gallery = httpx.get(url + "/api/templates", timeout=1)
                if gallery.status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.1)
        else:
            raise RuntimeError(f"Template screen mock did not start:\n{log_path.read_text(encoding='utf-8')}")
        approval = httpx.post(url + "/api/templates/import", json={"file": "{}"}, timeout=5)
        result = {
            "fixture_kind": "current screen-development mock; no template import implementation",
            "gallery_status": gallery.status_code,
            "import_status": approval.status_code,
            "import_body": approval.text,
            "mock_supports_import_approval_api": approval.status_code != 404,
        }
    finally:
        if process.poll() is None:
            if os.name == "nt":
                process.terminate()
            else:
                os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=10)
        log.close()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "template-approval-snapshot-mock.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
    )
    assert result["gallery_status"] == 200
    assert result["import_status"] == 404, "Unexpected mock import behavior; review the mock API before relying on it"
