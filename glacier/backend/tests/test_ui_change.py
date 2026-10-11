"""Acceptance tests for approval-gated UI change proposals."""
import subprocess
import json
import textwrap

import pytest

import ui_change


def _git_repo(path):
    path.mkdir(parents=True, exist_ok=True)
    (path / "glacier/web/src").mkdir(parents=True, exist_ok=True)
    (path / "glacier/web/src/screens").mkdir(parents=True, exist_ok=True)
    (path / "glacier/web/e2e").mkdir(parents=True, exist_ok=True)
    (path / "glacier/backend").mkdir(parents=True, exist_ok=True)
    (path / "glacier/web/e2e/home.spec.mjs").write_text("", encoding="utf-8")
    (path / "glacier/web/e2e/home_polish.spec.mjs").write_text("", encoding="utf-8")
    (path / "glacier/web/src/screens/Home.tsx").write_text("export const title = 'home';\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(path), "-c", "user.name=Test", "-c", "user.email=test@local",
                    "commit", "-qm", "base"], check=True)


def test_codex_draft_edits_source_and_returns_real_diff(tmp_path, monkeypatch):
    from routes import assistant_chat

    root = tmp_path / "repo"
    _git_repo(root)
    monkeypatch.setattr(ui_change, "ROOT", root)
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path / "home"))
    fake = tmp_path / "fake-codex.py"
    fake.write_text("#!/usr/bin/env python3\n" + textwrap.dedent('''
        import json, os, pathlib, sys
        args = sys.argv[1:]
        assert args[args.index("-s") + 1] == "workspace-write"
        cwd = pathlib.Path(args[args.index("-C") + 1])
        target = cwd / "glacier/web/src/screens/Home.tsx"
        target.write_text(target.read_text().replace("home", "welcome home"))
        answer = args[args.index("--") + 1]
        # The output file captures the engine's final explanation and spec.
        out = args[args.index("-o") + 1]
        pathlib.Path(out).write_text(json.dumps({"explanation":"Welcome home.","related_spec":"glacier/web/e2e/home.spec.mjs"}))
    '''), encoding="utf-8")
    fake.chmod(0o755)
    monkeypatch.setenv("GLACIER_CHAT_BIN", str(fake))
    result = assistant_chat._ui_change_draft("make the home title say welcome home", "codex", "shared context", "home", None)
    assert "+export const title = 'welcome home';" in result["diff"]
    assert result["explanation"] == "Welcome home."
    assert not list((tmp_path / "home" / "worktrees" / "ui-drafts").glob("*"))


def test_cli_draft_rejects_edits_outside_web_source(tmp_path, monkeypatch):
    from routes import assistant_chat

    root = tmp_path / "repo"
    _git_repo(root)
    monkeypatch.setattr(ui_change, "ROOT", root)
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path / "home"))
    fake = tmp_path / "fake-codex.py"
    fake.write_text("#!/usr/bin/env python3\n" + textwrap.dedent('''
        import json, pathlib, sys
        args = sys.argv[1:]
        cwd = pathlib.Path(args[args.index("-C") + 1])
        (cwd / "glacier/backend").mkdir(parents=True, exist_ok=True)
        (cwd / "glacier/backend/escape.py").write_text("bad\\n")
        out = args[args.index("-o") + 1]
        pathlib.Path(out).write_text(json.dumps({"explanation":"change","related_spec":"glacier/web/e2e/home.spec.mjs"}))
    '''), encoding="utf-8")
    fake.chmod(0o755)
    monkeypatch.setenv("GLACIER_CHAT_BIN", str(fake))
    with pytest.raises(ValueError, match="glacier/web/src"):
        assistant_chat._ui_change_draft("change home", "codex", "context", "home", None)


def test_missing_ui_source_returns_plain_setup_message(tmp_path, monkeypatch):
    from routes import assistant_chat

    monkeypatch.setattr(ui_change, "ROOT", tmp_path / "not-a-repo")
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path / "home"))
    result = assistant_chat._ui_change_source_error()
    assert result == "UI changes need the Glacier source folder. Set glacier_source_dir in GLACIER_HOME/settings.json to a Git repo containing glacier/web/src."


def test_glacier_source_setting_accepts_only_a_git_repo_with_web_source(tmp_path, monkeypatch):
    from routes import assistant_chat

    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("GLACIER_HOME", str(home))
    root = tmp_path / "configured-source"
    _git_repo(root)
    monkeypatch.setattr(assistant_chat, "available_engines", lambda: [{"id": "codex", "available": True, "reason": "ready"}])
    result = assistant_chat.save_ask_settings({"engine": "codex", "glacier_source_dir": str(root)})
    assert result["engine"] == "codex"
    assert json.loads((home / "settings.json").read_text(encoding="utf-8"))["glacier_source_dir"] == str(root.resolve())
    with pytest.raises(ValueError, match="Glacier source folder"):
        assistant_chat.save_ask_settings({"engine": "codex", "glacier_source_dir": str(tmp_path / "missing")})


def test_model_edit_blocks_create_diff_and_bad_block_gets_one_repair(tmp_path, monkeypatch):
    from routes import assistant_chat

    root = tmp_path / "repo"
    _git_repo(root)
    monkeypatch.setattr(ui_change, "ROOT", root)
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path / "home"))
    calls = []
    def fake_engine(prompt, route, schema=None):
        calls.append((prompt, schema))
        if "repair the edit blocks" in prompt.lower():
            return {"edits": [{"file": "glacier/web/src/screens/Home.tsx", "find": "title = 'home'", "replace": "title = 'welcome home'"}],
                    "explanation": "Welcome home.", "related_spec": "home screen"}
        return {"edits": [{"file": "glacier/web/src/screens/Home.tsx", "find": "does not exist", "replace": "x"}]}
    monkeypatch.setattr(assistant_chat, "_ask_engine", fake_engine)
    result = assistant_chat._ui_change_draft("make the home title welcome", "local", "context", "home", None)
    assert "+export const title = 'welcome home';" in result["diff"]
    assert result["related_spec"] == "glacier/web/e2e/home_polish.spec.mjs"
    assert len(calls) == 2
    assert "export const title" in calls[0][0]


def test_ui_change_proposal_accepts_only_src_unified_diff():
    proposal = ui_change.propose(
        "diff --git a/glacier/web/src/App.tsx b/glacier/web/src/App.tsx\n"
        "--- a/glacier/web/src/App.tsx\n+++ b/glacier/web/src/App.tsx\n@@ -1 +1 @@\n-old\n+new\n",
        "Make the welcome message clearer.", "glacier/web/e2e/core.spec.mjs")
    assert proposal["kind"] == "ui_change"
    assert proposal["explanation"] == "Make the welcome message clearer."
    assert "glacier/web/src/App.tsx" in proposal["diff"]


@pytest.mark.parametrize("message", ["make the home title say 'welcome home'", "change this screen color", "update Glacier's UI"])
def test_natural_ui_change_requests_are_detected(message):
    from routes import assistant_chat

    assert assistant_chat._ui_change_requested(message)


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
