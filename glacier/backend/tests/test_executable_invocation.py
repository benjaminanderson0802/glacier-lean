import shell_commands


def test_windows_bare_name_resolves_to_the_cmd_shim(monkeypatch):
    monkeypatch.setattr(shell_commands.os, "name", "nt")
    monkeypatch.setattr(shell_commands, "which", lambda name: r"C:\\Users\\me\\AppData\\Roaming\\npm\\codex.CMD" if name == "codex" else None)
    assert shell_commands.executable_invocation("codex", "login", "status") == [r"C:\\Users\\me\\AppData\\Roaming\\npm\\codex.CMD", "login", "status"]


def test_windows_unknown_bare_name_is_left_alone(monkeypatch):
    monkeypatch.setattr(shell_commands.os, "name", "nt")
    monkeypatch.setattr(shell_commands, "which", lambda name: None)
    assert shell_commands.executable_invocation("nothing-here", "x") == ["nothing-here", "x"]


def test_windows_python_helper_runs_through_the_interpreter(monkeypatch):
    monkeypatch.setattr(shell_commands.os, "name", "nt")
    monkeypatch.setattr(shell_commands, "which", lambda name: None)
    out = shell_commands.executable_invocation(r"C:\\tools\\fake.py", "a")
    assert out[0] == shell_commands.sys.executable and out[1:] == [r"C:\\tools\\fake.py", "a"]


def test_posix_is_unchanged(monkeypatch):
    monkeypatch.setattr(shell_commands.os, "name", "posix")
    assert shell_commands.executable_invocation("codex", "login") == ["codex", "login"]
