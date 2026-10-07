import os
import socket
import subprocess

import pytest

import sandboxing


def _sandbox_or_skip():
    available, reason = sandboxing.available()
    if not available:
        pytest.skip(f"OS sandbox unavailable: {reason}")


def _run(command, workdir):
    return subprocess.run(
        sandboxing.wrap(command, str(workdir), []),
        cwd=workdir,
        text=True,
        capture_output=True,
        timeout=10,
    )


def test_sandbox_blocks_writes_outside_workdir(tmp_path):
    _sandbox_or_skip()
    workdir = tmp_path / "work"
    workdir.mkdir()
    outside = tmp_path / "outside.txt"

    result = _run(f"echo escaped > {outside}", workdir)

    assert result.returncode != 0
    assert not outside.exists()


def test_sandbox_can_read_system_hostname(tmp_path):
    _sandbox_or_skip()
    workdir = tmp_path / "work"
    workdir.mkdir()

    result = _run("cat /etc/hostname", workdir)

    assert result.returncode == 0
    assert result.stdout.strip()


def test_sandbox_blocks_network_when_allowlist_is_empty(tmp_path):
    _sandbox_or_skip()
    workdir = tmp_path / "work"
    workdir.mkdir()
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    host, port = server.getsockname()
    try:
        result = _run(
            f"python -c 'import socket; s=socket.create_connection(({host!r}, {port}), timeout=1)'",
            workdir,
        )
    finally:
        server.close()

    assert result.returncode != 0


def test_sandbox_preserves_command_output_and_exit_code(tmp_path):
    _sandbox_or_skip()
    workdir = tmp_path / "work"
    workdir.mkdir()

    result = _run("printf 'hello sandbox\\n'; exit 7", workdir)

    assert result.stdout == "hello sandbox\n"
    assert result.stderr == ""
    assert result.returncode == 7


def test_nonempty_host_allowlist_is_rejected_until_proxy_exists(tmp_path):
    with pytest.raises(NotImplementedError, match="proxy"):
        sandboxing.wrap("true", str(tmp_path), ["example.com"])
