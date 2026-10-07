"""Acceptance checks for the recovery benchmark's schema, hashing and fake API."""
from __future__ import annotations

import importlib.util
from pathlib import Path


RUNNER = Path(__file__).with_name("run_glacier.py")
SPEC = importlib.util.spec_from_file_location("recover_runner_acceptance", RUNNER)
recover = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recover)


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        import json
        return json.dumps(self.body).encode()


def test_hashes_ignore_file_names_and_detect_content_change(tmp_path):
    first = tmp_path / "a.txt"
    second = tmp_path / "b.txt"
    first.write_text("before", encoding="utf-8")
    second.write_text("before", encoding="utf-8")
    assert recover.file_hash(first) == recover.file_hash(second)
    second.write_text("after", encoding="utf-8")
    assert recover.file_hash(first) != recover.file_hash(second)


def test_recovery_case_matrix_covers_four_required_actions():
    assert [case["id"] for case in recover.CASES] == [
        "run_notes", "flow_restore", "memory_undo", "isolated_code_undo"
    ]
    assert all(case["recovery_path"].startswith("/api/") for case in recover.CASES)


def test_api_request_encodes_body_and_decodes_json(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse({"ok": True})

    monkeypatch.setattr(recover.urllib.request, "urlopen", fake_urlopen)
    assert recover.request("http://local", "POST", "/api/test", {"value": 1}) == {"ok": True}
    assert captured["request"].get_method() == "POST"
    assert captured["request"].get_header("Content-type") == "application/json"
    assert captured["timeout"] > 0


def test_report_records_threshold_and_audit_coverage():
    rows = [
        {"id": "run_notes", "seconds": 0.5, "recovered": True, "audit_expected": 50, "audit_found": 50, "detail": "test"},
        {"id": "flow_restore", "seconds": 1.0, "recovered": True, "audit_expected": 1, "audit_found": 1, "detail": "test"},
        {"id": "memory_undo", "seconds": 2.0, "recovered": True, "audit_expected": 1, "audit_found": 1, "detail": "test"},
        {"id": "isolated_code_undo", "seconds": 2.5, "recovered": True, "audit_expected": 1, "audit_found": 1, "detail": "test"},
    ]
    report, passed = recover.build_report(rows)
    assert passed
    assert "100.00%" in report
    assert "120 s" in report
