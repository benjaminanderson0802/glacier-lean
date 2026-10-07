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
    monkeypatch.setenv("GLACIER_TOKEN", "benchmark-token")

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse({"ok": True})

    monkeypatch.setattr(recover.urllib.request, "urlopen", fake_urlopen)
    assert recover.request("http://local", "POST", "/api/test", {"value": 1}) == {"ok": True}
    assert captured["request"].get_method() == "POST"
    assert captured["request"].get_header("Content-type") == "application/json"
    assert captured["request"].get_header("Authorization") == "Bearer benchmark-token"
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


def test_recovery_timer_polls_until_state_is_restored(monkeypatch):
    ticks = iter([10.0, 10.0, 10.1, 10.2, 10.3, 10.4])
    monkeypatch.setattr(recover.time, "monotonic", lambda: next(ticks, 10.4))
    sleeps = []
    monkeypatch.setattr(recover.time, "sleep", lambda delay: sleeps.append(delay))
    checks = iter([False, False, True])
    elapsed, restored, error = recover.timed_recovery(lambda: None, lambda: next(checks))
    assert elapsed < 0.5
    assert restored is True
    assert error == ""
    assert sleeps == [0.1, 0.1]


def test_recovery_timer_reports_step_and_times_out_when_check_stalls(monkeypatch, capsys):
    import time
    monkeypatch.setattr(recover, "LIMIT_SECONDS", 0.5)
    real_sleep = time.sleep
    monkeypatch.setattr(recover.time, "sleep", lambda delay: real_sleep(min(delay, 0.01)))
    elapsed, restored, error = recover.timed_recovery(
        lambda: None, lambda: real_sleep(2), step="undo 50-note run", progress=False
    )
    assert elapsed >= 0.5
    assert restored is False
    assert "undo 50-note run" in error
    assert "timed out" in error.casefold()


def test_recovery_timer_logs_named_step(monkeypatch, capsys):
    monkeypatch.setattr(recover, "LIMIT_SECONDS", 0.5)
    elapsed, restored, _error = recover.timed_recovery(
        lambda: None, lambda: True, step="undo overwritten note"
    )
    assert restored is True
    assert "[undo overwritten note]" in capsys.readouterr().out


def test_tree_snapshot_excludes_git_and_index_files(tmp_path):
    (tmp_path / "note.md").write_text("note", encoding="utf-8")
    (tmp_path / "index.sqlite").write_text("index", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("git", encoding="utf-8")
    snapshot = recover.tree_snapshot(tmp_path)
    assert set(snapshot) == {"note.md"}


def test_expected_audit_counts_run_side_effects_not_recovery_requests():
    assert recover.expected_audit_count(changed_files=50, recovery_requests=1) == 51
    assert recover.expected_audit_count(changed_files=10, recovery_requests=1) == 11
    assert recover.expected_audit_count(changed_files=1, recovery_requests=1) == 2


def test_audit_recovery_request_counts_returned_commit_id(tmp_path):
    repo = tmp_path / "vault"
    repo.mkdir()
    import subprocess
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "test"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.invalid"], check=True)
    (repo / "note.md").write_text("note", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "note.md"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "Undo changes from run abc"], check=True)
    commit = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    assert recover.audit_recovery_commit_count(repo, commit[:8]) == 1
    assert recover.audit_recovery_commit_count(repo, "not-a-commit") == 0


def test_tree_snapshot_detects_added_changed_and_removed_files(tmp_path):
    (tmp_path / "before.txt").write_text("before", encoding="utf-8")
    before = recover.tree_snapshot(tmp_path)
    (tmp_path / "before.txt").write_text("changed", encoding="utf-8")
    (tmp_path / "added.txt").write_text("added", encoding="utf-8")
    after = recover.tree_snapshot(tmp_path)
    assert recover.snapshot_diff(before, after) == {"added.txt", "before.txt"}


def test_backend_diagnostics_use_log_file_and_sigusr1_hook(tmp_path):
    import inspect
    source = inspect.getsource(recover.start_backend)
    assert "log_path.open" in source
    assert "faulthandler.register(signal.SIGUSR1" in (Path(recover.__file__).with_name("run_glacier.py").parent / "run_glacier.py").read_text()
    assert "GLACIER_MAX_PARALLEL_RUNS" in source
