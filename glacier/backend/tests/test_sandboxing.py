import socket
import subprocess
import os

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


def test_seccomp_checks_architecture_before_syscall_number():
    instructions = sandboxing._seccomp_instructions("x86_64")
    assert instructions[0].code == sandboxing._BPF_LD_W_ABS
    assert instructions[0].k == 4  # seccomp_data.arch
    assert instructions[1].code == sandboxing._BPF_JMP_JEQ_K
    assert instructions[1].k == 0xC000003E
    assert instructions[2].k == sandboxing._SECCOMP_RET_KILL_PROCESS


def test_sandbox_does_not_expose_parent_environment(tmp_path, monkeypatch):
    _sandbox_or_skip()
    workdir = tmp_path / "work"
    workdir.mkdir()
    monkeypatch.setenv("GLACIER_TEST_SECRET", "do-not-leak")

    result = _run("test -z \"${GLACIER_TEST_SECRET+x}\"", workdir)

    assert result.returncode == 0


def test_sandbox_allows_standard_null_device(tmp_path):
    _sandbox_or_skip()
    workdir = tmp_path / "work"
    workdir.mkdir()

    result = _run("echo hi >/dev/null", workdir)

    assert result.returncode == 0


def test_sandbox_creates_writable_tmp_directory(tmp_path):
    _sandbox_or_skip()
    workdir = tmp_path / "work"
    workdir.mkdir()

    result = _run("test -d \"$TMPDIR\" && touch \"$TMPDIR/file\"", workdir)

    assert result.returncode == 0


def test_sandbox_allows_reading_urandom(tmp_path):
    _sandbox_or_skip()
    workdir = tmp_path / "work"
    workdir.mkdir()

    result = _run("head -c 1 /dev/urandom | wc -c", workdir)

    assert result.returncode == 0
    assert result.stdout.strip() == "1"


def test_sandbox_refuses_signal_to_all_processes(tmp_path):
    _sandbox_or_skip()
    workdir = tmp_path / "work"
    workdir.mkdir()

    result = _run("kill -0 -1", workdir)

    assert result.returncode != 0
    assert "operation not permitted" in result.stderr.lower()


def test_sandbox_documents_known_pid_signal_fallback_limitation():
    from pathlib import Path

    docs = Path(__file__).resolve().parents[3] / "docs" / "SANDBOXING.md"
    assert "can still signal a specific same-user process" in docs.read_text(encoding="utf-8")


def test_sandbox_refuses_signal_zero_to_parent_on_landlock_abi_six(tmp_path):
    """ABI < 6 cannot distinguish this PID; ABI 6 scopes signals to the sandbox."""
    _sandbox_or_skip()
    abi = sandboxing._landlock_abi()
    if abi < 6:
        pytest.skip(f"Landlock ABI {abi} cannot restrict signals to the sandbox process tree")

    workdir = tmp_path / "work"
    workdir.mkdir()
    parent_pid = os.getpid()

    result = _run(f"kill -0 {parent_pid}", workdir)

    assert result.returncode != 0
    assert "operation not permitted" in result.stderr.lower()


def test_available_reports_subprocess_failures(monkeypatch):
    def fail(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs.get("timeout"))

    monkeypatch.setattr(sandboxing.subprocess, "run", fail)

    available, reason = sandboxing.available()

    assert not available
    assert "timed out" in reason.lower()


def test_nonempty_host_allowlist_is_rejected_until_proxy_exists(tmp_path):
    with pytest.raises(NotImplementedError, match="proxy"):
        sandboxing.wrap("true", str(tmp_path), ["example.com"])
