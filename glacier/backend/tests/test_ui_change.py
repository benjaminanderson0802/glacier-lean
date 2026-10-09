"""Acceptance tests for approval-gated UI change proposals."""
import subprocess

import pytest

import ui_change


def test_ui_change_proposal_accepts_only_src_unified_diff():
    proposal = ui_change.propose(
        "diff --git a/glacier/web/src/App.tsx b/glacier/web/src/App.tsx\n"
        "--- a/glacier/web/src/App.tsx\n+++ b/glacier/web/src/App.tsx\n@@ -1 +1 @@\n-old\n+new\n",
        "Make the welcome message clearer.", "glacier/web/e2e/core.spec.mjs")
    assert proposal["kind"] == "ui_change"
    assert proposal["explanation"] == "Make the welcome message clearer."
    assert "glacier/web/src/App.tsx" in proposal["diff"]


@pytest.mark.parametrize("path", ["../secrets.txt", "glacier/backend/app.py", "/tmp/x"])
def test_ui_change_rejects_paths_outside_web_src(path):
    diff = f"--- a/{path}\n+++ b/{path}\n@@ -1 +1 @@\n-old\n+new\n"
    with pytest.raises(ValueError, match="glacier/web/src"):
        ui_change.validate_diff(diff)


def test_apply_runs_every_check_and_reports_each_result(tmp_path, monkeypatch):
    called = []
    def run(args, cwd, timeout=900):
        called.append(args)
        return {"passed": args[0] != "npx", "exit_code": 0 if args[0] != "npx" else 1, "output": ""}
    monkeypatch.setattr(ui_change, "_command", run)
    outcome = ui_change._run_checks(tmp_path, "glacier/web/e2e/shell.spec.mjs")
    assert [args[0] for args in called] == ["npx", "node", "npm", "node"]
    assert outcome["passed"] is False
    assert set(outcome["results"]) == {"tsc", "theme lint", "build", "e2e"}


def test_chat_ui_change_proposal_never_applies_before_approval(tmp_path, monkeypatch):
    monkeypatch.setattr(ui_change, "ROOT", tmp_path)
    home = tmp_path / "home"
    monkeypatch.setenv("GLACIER_HOME", str(home))
    source = tmp_path / "glacier/web/src"
    source.mkdir(parents=True)
    (source / "App.tsx").write_text("old\n", encoding="utf-8")
    (tmp_path / "glacier/web/e2e").mkdir(parents=True)
    (tmp_path / "glacier/web/e2e/core.spec.mjs").write_text("", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "-c", "user.name=Test", "-c", "user.email=test@local",
                    "commit", "-qm", "base"], check=True)
    monkeypatch.setattr(ui_change, "_run_checks", lambda *_: {"passed": True, "results": {
        "tsc": {"passed": True}, "theme lint": {"passed": True}, "e2e": {"passed": True}}})
    proposal = ui_change.propose(
        "--- a/glacier/web/src/App.tsx\n+++ b/glacier/web/src/App.tsx\n@@ -1 +1 @@\n-old\n+new\n",
        "A clearer welcome.", "glacier/web/e2e/core.spec.mjs")
    assert (tmp_path / "glacier/web/src/App.tsx").read_text() == "old\n"
    result = ui_change.apply(proposal["id"])
    assert result["branch"].startswith("assistant/ui-change/")
    assert (tmp_path / "glacier/web/src/App.tsx").read_text() == "old\n"
    assert (home / "worktrees" / "ui-changes" / proposal["id"] / "glacier/web/src/App.tsx").read_text() == "new\n"
    assert {"tsc", "theme lint", "e2e"}.issubset(set(result["checks"]))
