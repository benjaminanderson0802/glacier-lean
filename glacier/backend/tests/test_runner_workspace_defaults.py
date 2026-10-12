"""Regression checks for model and relative-folder defaults in real flow runs."""

import runner


def test_relative_command_folder_is_resolved_from_the_flow_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    notes = workspace / "notes"
    notes.mkdir(parents=True)

    result = runner.run_command({"cmd": "pwd", "cwd": "notes"}, timeout=5, ws=str(workspace))

    assert result["exit_code"] == 0
    assert result["output"].strip() == str(notes)


def test_default_codex_model_does_not_become_an_explicit_cli_model():
    assert runner._codex_model_args({"model": "default"}) == []
    assert runner._codex_model_args({"model": "gpt-6-codex"}) == ["-m", "gpt-6-codex"]
