"""Acceptance tests for local file and webhook starts."""
import json
import os
import re
import time

import httpx
import pytest

from conftest import Server, env, raw_httpx
import triggers


def test_file_trigger_normalizes_path_to_absolute_native_spelling(tmp_path):
    (tmp_path / "folder").mkdir()
    relative = tmp_path / "folder" / ".." / "folder" / "file.txt"
    assert triggers._native_absolute_path(relative) == str(relative.resolve())


def _as_command_sees(path):
    """Command steps run in Git Bash on Windows, so the runner hands them /c/Users/... paths."""
    value = str(path)
    match = re.match(r"^([A-Za-z]):[\\/](.*)$", value) if os.name == "nt" else None
    return "/" + match.group(1).lower() + "/" + match.group(2).replace("\\", "/") if match else value


def _trigger_flow(folder, *, enabled=True, env_id="file-start"):
    flow = env(env_id, [
        ("start", "file_trigger", {"folder": str(folder), "pattern": "*.txt"}),
        ("use", "command", {"cmd": "printf '%s' {trigger_file}"}),
    ], [("start", "use", "")])
    flow["enabled"] = enabled
    return flow


def _wait_for_runs(server, count, timeout=8):
    deadline = time.monotonic() + timeout
    runs = []
    while time.monotonic() < deadline:
        runs = server.get("/api/runs?env_id=file-start")
        if len(runs) >= count:
            return runs
        time.sleep(0.05)
    raise AssertionError(f"expected {count} runs, saw {len(runs)}: {runs}")


def test_file_trigger_finds_new_files_once_across_restart(tmp_path, monkeypatch):
    folder = tmp_path / "watched folder"
    folder.mkdir()
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("GLACIER_TRIGGER_POLL_SECONDS", "0.1")
    s = Server(home).start()
    try:
        s.put("/api/environments/file-start", _trigger_flow(folder))
        first = folder / "first.txt"
        first.write_text("first")
        runs = _wait_for_runs(s, 1)
        one = s.wait_run(runs[0]["run_id"])
        assert one["trigger"]["type"] == "file"
        assert one["trigger"]["file"] == str(first)
        assert one["outputs"]["use"] == _as_command_sees(first)
        s.kill()
        (home / "triggers.sqlite").unlink()
        s.start()
        time.sleep(0.5)
        assert s.get("/api/runs?env_id=file-start").__len__() == 1
        second = folder / "second.txt"
        second.write_text("second")
        runs = _wait_for_runs(s, 2)
        two = s.wait_run(next(r["run_id"] for r in runs if r["run_id"] != one["run_id"]))
        assert two["outputs"]["use"] == _as_command_sees(second)
        assert len(s.get("/api/runs?env_id=file-start")) == 2
    finally:
        s.stop()


def test_file_trigger_refuses_glacier_data_folder(server, tmp_path):
    flow = _trigger_flow(tmp_path, env_id="unsafe-file-start")
    flow["nodes"][0]["config"]["folder"] = server.home
    response = raw_httpx["put"](server.url + "/api/environments/unsafe-file-start", json=flow,
                                  headers={"Authorization": "Bearer glacier-test-token"})
    assert response.status_code == 400
    assert "Glacier's data folder" in response.text


def test_webhook_requires_token_and_records_body_without_echo(server):
    webhook = env("hooked", [
        ("start", "webhook_trigger", {}),
        ("use", "command", {"cmd": "printf '%s' {trigger_body}"}),
    ], [("start", "use", "")])
    server.put("/api/environments/hooked", webhook)
    url = server.url + "/api/hooks/hooked"
    denied = raw_httpx["post"](url, json={"message": "private"}, headers={"Origin": server.url})
    assert denied.status_code == 401
    accepted = raw_httpx["post"](url, json={"message": "hello", "api_key": "dont-echo-this"}, headers={
        "Authorization": "Bearer glacier-test-token", "Origin": server.url,
    })
    assert accepted.status_code == 202
    payload = accepted.json()
    assert "hello" not in accepted.text
    run = server.wait_run(payload["run_id"])
    assert run["trigger"] == {"type": "webhook", "node_id": "start"}
    assert run["outputs"]["start"] == '{"message":"hello","api_key":"[redacted]"}'
    assert run["outputs"]["use"] == '{"message":"hello","api_key":"[redacted]"}'
    assert "dont-echo-this" not in accepted.text


def test_webhook_rejects_oversized_body(server):
    server.put("/api/environments/too-big", env("too-big", [("start", "webhook_trigger", {})], []))
    body = b'{"data":"' + b"x" * (1024 * 1024) + b'"}'
    response = raw_httpx["post"](server.url + "/api/hooks/too-big", content=body, headers={
        "Authorization": "Bearer glacier-test-token", "Origin": server.url,
        "Content-Type": "application/json",
    })
    assert response.status_code == 413
    assert "x" * 50 not in response.text


def test_disabled_flow_ignores_webhook(server):
    flow = env("disabled-hook", [("start", "webhook_trigger", {})], [])
    flow["enabled"] = False
    server.put("/api/environments/disabled-hook", flow)
    response = raw_httpx["post"](server.url + "/api/hooks/disabled-hook", json={"ok": True}, headers={
        "Authorization": "Bearer glacier-test-token", "Origin": server.url,
    })
    assert response.status_code == 409
    assert server.get("/api/runs?env_id=disabled-hook") == []


def test_disabled_file_trigger_does_not_start(server, tmp_path, monkeypatch):
    folder = tmp_path.parent / f"{tmp_path.name}-paused"
    folder.mkdir()
    monkeypatch.setenv("GLACIER_TRIGGER_POLL_SECONDS", "0.1")
    flow = _trigger_flow(folder, enabled=False, env_id="paused-file")
    server.put("/api/environments/paused-file", flow)
    (folder / "waiting.txt").write_text("later")
    time.sleep(0.4)
    assert server.get("/api/runs?env_id=paused-file") == []
    (folder / "waiting.txt").unlink()
    folder.rmdir()
