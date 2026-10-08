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


_RUNNABLE_WINDOWS = (".exe", ".cmd", ".bat", ".com")


def which(name: str) -> str | None:
    """Find a program the way Windows can actually start it.

    npm puts an extensionless shell script (for example ``codex``) next to ``codex.cmd``.
    Starting that script on Windows shows an "Unsupported 16-bit application" box and
    blocks until someone closes it, so on Windows only .exe/.cmd/.bat/.com files count.
    """
    if not name:
        return None
    found = shutil.which(name)
    if os.name != "nt":
        return found
    if not found:
        return None  # shutil.which already tried PATHEXT; nothing runnable here
    # .py helpers are fine too: executable_invocation runs them with the current Python.
    if os.path.splitext(found)[1].lower() in _RUNNABLE_WINDOWS + (".py",) or not os.path.isfile(found):
        return found
    exts = [e.lower() for e in os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(";") if e]
    exts = [e for e in exts if e in _RUNNABLE_WINDOWS] or list(_RUNNABLE_WINDOWS)
    base, ext = os.path.splitext(name)
    candidates = [name] if ext.lower() in _RUNNABLE_WINDOWS else [name + e for e in exts]
    if os.path.dirname(name):
        return next((c for c in candidates if os.path.isfile(c)), None)
    for folder in [d for d in os.environ.get("PATH", "").split(os.pathsep) if d]:
        for candidate in candidates:
            full = os.path.join(folder, candidate)
            if os.path.isfile(full):
                return full
    return None
