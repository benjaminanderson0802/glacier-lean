"""Independent attacks against acceptance files protected by PH3.2 (I-04)."""
import os
import shlex
import sys
from pathlib import Path

import httpx
import pytest

from conftest import Server, env


@pytest.fixture(scope="module")
def protected_server(tmp_path_factory):
    server = Server(tmp_path_factory.mktemp("protected-path-attacks")).start()
    yield server
    server.stop()


def _flow(env_id, command, protected_path="check.sh", check_content="exit 0\n"):
    graph = env(env_id, [("work", "command", {"cmd": command})], [])
    graph["goal"] = "Produce work that passes its protected check"
    graph["acceptance"] = [{
        "kind": "command",
        "cmd": "sh check.sh" if protected_path == "check.sh" else f"sh {protected_path}",
        "files": {protected_path: check_content},
    }]
    return graph


def _python_command(code):
    return f"{shlex.quote(sys.executable)} -c {shlex.quote(code)}"


def _workspace(server, env_id):
    return Path(server.home) / "workspaces" / env_id


def _run(server, env_id, command, protected_path="check.sh", check_content="exit 0\n"):
    server.put(f"/api/environments/{env_id}", _flow(env_id, command, protected_path, check_content))
    return server.wait_run(server.post(f"/api/environments/{env_id}/run")["run_id"])


def _assert_rejected(run, evidence_fragment):
    assert run["status"] == "failed" and run["verified"] is False, run
    assert len(run["verification"]) == 1, run["verification"]
    verification = run["verification"][0]
    assert verification["passed"] is False, verification
    assert evidence_fragment in verification["evidence"], verification
    assert "not accepted" in verification["evidence"], verification


@pytest.mark.parametrize("link_kind", ["file", "parent", "dangling"])
def test_protected_symlinks_fail_without_writing_outside_workspace(protected_server, tmp_path, link_kind):
    """File, parent-directory, and dangling links cannot redirect verifier restoration."""
    env_id = f"protected-{link_kind}-link"
    outside = tmp_path / f"outside-{link_kind}"
    outside.mkdir()
    sentinel = outside / "check.sh"
    sentinel.write_text("outside sentinel\n", encoding="utf-8")
    before = sentinel.read_bytes()
    redirected_target = sentinel

    if link_kind == "file":
        code = f"import os; os.symlink({str(sentinel)!r}, 'check.sh')"
        expected = "protected check path is a link"
    elif link_kind == "parent":
        code = f"import os; os.symlink({str(outside)!r}, 'linked-dir', target_is_directory=True)"
        expected = "protected check path is a link"
    else:
        dangling = outside / "does-not-exist"
        redirected_target = dangling
        code = f"import os; os.symlink({str(dangling)!r}, 'check.sh')"
        expected = "protected check path is a link"

    protected_path = "linked-dir/check.sh" if link_kind == "parent" else "check.sh"
    if os.name == "nt":
        try:
            os.symlink(str(outside), tmp_path / "symlink-capability-probe", target_is_directory=True)
            (tmp_path / "symlink-capability-probe").unlink()
        except (OSError, NotImplementedError):
            pytest.skip("creating symlinks requires Windows developer mode or elevation")

    run = _run(protected_server, env_id, _python_command(code), protected_path)
    _assert_rejected(run, expected)
    assert sentinel.read_bytes() == before
    if link_kind == "dangling":
        assert not redirected_target.exists()


def test_non_regular_protected_path_fails_with_evidence(protected_server):
    run = _run(protected_server, "protected-directory", _python_command("import os; os.mkdir('check.sh')"))
    _assert_rejected(run, "protected check path has the wrong file type")


def test_deleting_preexisting_check_fails_and_is_reported(protected_server):
    env_id = "protected-delete"
    protected = _workspace(protected_server, env_id) / "check.sh"
    protected.parent.mkdir(parents=True, exist_ok=True)
    protected.write_text("exit 0\n", encoding="utf-8")

    run = _run(protected_server, env_id, _python_command("import os; os.unlink('check.sh')"))
    _assert_rejected(run, "worker deleted protected check file check.sh during the run")


def test_creating_previously_absent_check_fails_even_with_saved_contents(protected_server):
    code = "from pathlib import Path; Path('check.sh').write_text('exit 0\\n', encoding='utf-8')"
    run = _run(protected_server, "protected-create", _python_command(code))
    _assert_rejected(run, "worker created protected check file check.sh during the run")


def test_replacing_protected_content_cannot_be_silently_accepted(protected_server):
    protected = _workspace(protected_server, "protected-replace") / "check.sh"
    protected.parent.mkdir(parents=True, exist_ok=True)
    protected.write_text("exit 0\n", encoding="utf-8")
    code = "from pathlib import Path; Path('check.sh').write_text('exit 1\\n', encoding='utf-8')"
    run = _run(protected_server, "protected-replace", _python_command(code))
    _assert_rejected(run, "worker changed protected check file check.sh during the run")


@pytest.mark.parametrize("path", [
    "../outside-check.sh",
    r"..\outside-check.sh",
    r"C:\outside-check.sh",
    r"\\server\share\outside-check.sh",
])
def test_portable_traversal_paths_are_rejected_when_flow_is_saved(protected_server, path):
    env_id = "protected-traversal"
    response = httpx.put(
        protected_server.url + f"/api/environments/{env_id}",
        json=_flow(env_id, _python_command("pass"), path),
        timeout=30,
    )
    assert response.status_code == 400, response.text
    assert "outside the workspace" in response.json()["detail"]


def test_verifier_only_file_may_be_absent_before_work_and_stays_private(protected_server):
    env_id = "protected-verifier-only"
    workspace = _workspace(protected_server, env_id)
    run = _run(protected_server, env_id, _python_command("pass"))

    assert run["status"] == "done" and run["verified"] is True, run
    assert run["verification"][0]["passed"] is True, run["verification"]
    assert not os.path.lexists(workspace / "check.sh")
