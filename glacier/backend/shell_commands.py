"""Choose a shell for configured commands while keeping Linux behavior unchanged."""
import os
import re
import shutil
import sys
import threading


_fallback_warning_lock = threading.Lock()
_fallback_warning_emitted = False


def command_invocation(command: str):
    """Return (argv, use_shell, warning) for a configured shell command."""
    if os.name != "nt":
        return command, True, ""

    bash = shutil.which("bash")
    if not bash:
        candidate = r"C:\Program Files\Git\bin\bash.exe"
        if os.path.isfile(candidate):
            bash = candidate
    if bash:
        def windows_path(match):
            drive = match.group(1).lower()
            path = match.group(2).replace("\\", "/")
            return f"/{drive}/{path}"

        command = re.sub(r"(?<![A-Za-z0-9_])([A-Za-z]):\\([^\s\"';&|<>]+)", windows_path, command)
        return [bash, "-lc", command], False, ""

    global _fallback_warning_emitted
    with _fallback_warning_lock:
        warning = ""
        if not _fallback_warning_emitted:
            warning = "Git Bash was not found; this command is running in Windows Command Prompt.\n"
            _fallback_warning_emitted = True
    raise RuntimeError(warning.strip() or "Git Bash was not found; install Git for Windows to run this command")


def executable_invocation(executable: str, *args: str) -> list[str]:
    """Run Python helpers through the current interpreter on Windows."""
    if os.name == "nt" and executable.lower().endswith(".py"):
        return [sys.executable, executable, *args]
    return [executable, *args]
