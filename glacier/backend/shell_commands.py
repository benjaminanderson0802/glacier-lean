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
    # Prefer Git for Windows over the Windows Subsystem for Linux bash.exe
    # alias, which can exist earlier on PATH but cannot run without a distro.
    candidate = r"C:\Program Files\Git\bin\bash.exe"
    if os.path.isfile(candidate):
        bash = candidate
    elif bash and os.path.normcase(os.path.abspath(bash)) == os.path.normcase(
        r"C:\Windows\System32\bash.exe"
    ):
        bash = None
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
    """Build an argv that Windows can actually start.

    Python helpers run through the current interpreter. A bare program name ("codex") is resolved
    to its full path first: npm installs CLIs as ``codex.cmd`` shims, and Windows cannot start a
    .cmd by bare name without a shell (FileNotFoundError), which made a signed-in Codex look missing.
    """
    if os.name == "nt":
        if not os.path.dirname(executable):
            found = which(executable)
            if found:
                executable = found
        if executable.lower().endswith(".py"):
            return [sys.executable, executable, *args]
        if executable.lower().endswith((".cmd", ".bat")):
            direct = npm_shim_command(executable)
            if direct:
                return [*direct, *args]
    return [executable, *args]


_NPM_SHIM_SCRIPT = re.compile(r'"%dp0%\\([^"]+\.(?:js|cjs|mjs))"', re.IGNORECASE)


def npm_shim_command(shim: str) -> list[str] | None:
    """Return [node, script] for an npm-generated .cmd shim, or None.

    Windows starts a .cmd through cmd.exe, which cuts every argument at its first newline, so a
    multi-line prompt passed to ``codex.cmd`` or ``claude.cmd`` reached the model as only its first
    line ("Shared context pack:"). Starting node on the shim's script directly keeps arguments whole.
    """
    try:
        with open(shim, encoding="utf-8", errors="replace") as handle:
            text = handle.read(8192)
    except OSError:
        return None
    match = _NPM_SHIM_SCRIPT.search(text)
    if not match:
        return None
    folder = os.path.dirname(os.path.abspath(shim))
    script = os.path.join(folder, match.group(1).replace("/", os.sep).replace("\\", os.sep))
    if not os.path.isfile(script):
        return None
    bundled = os.path.join(folder, "node.exe")
    node = bundled if os.path.isfile(bundled) else (shutil.which("node") or "")
    if not node:
        return None
    return [node, script]


_RUNNABLE_WINDOWS = (".exe", ".cmd", ".bat", ".com")


def _startable(path: str) -> bool:
    """True when Windows can start this file without a blocking error box.

    A broken install can leave a file named ``ollama.exe`` that is really a zip archive
    (seen on a real PC: a winget link to an unextracted download). Starting it shows an
    "Unsupported 16-bit application" box and blocks the caller, so a program file must
    begin with the "MZ" program header.
    """
    if not os.path.isfile(path):
        return False
    if os.path.splitext(path)[1].lower() not in (".exe", ".com"):
        return True
    try:
        with open(path, "rb") as handle:
            return handle.read(2) == b"MZ"
    except OSError:
        return False


def which(name: str) -> str | None:
    """Find a program the way Windows can actually start it.

    npm puts an extensionless shell script (for example ``codex``) next to ``codex.cmd``.
    Starting that script on Windows shows an "Unsupported 16-bit application" box and
    blocks until someone closes it, so on Windows only .exe/.cmd/.bat/.com files count,
    and a .exe/.com must really be a program (see ``_startable``). When the first match
    on PATH cannot start, later folders on PATH are tried.
    """
    if not name:
        return None
    found = shutil.which(name)
    if os.name != "nt":
        return found
    if not found:
        return None  # shutil.which already tried PATHEXT; nothing runnable here
    if not os.path.isfile(found):
        return found
    # .py helpers are fine too: executable_invocation runs them with the current Python.
    if os.path.splitext(found)[1].lower() in _RUNNABLE_WINDOWS + (".py",) and _startable(found):
        return found
    exts = [e.lower() for e in os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(";") if e]
    exts = [e for e in exts if e in _RUNNABLE_WINDOWS] or list(_RUNNABLE_WINDOWS)
    base, ext = os.path.splitext(name)
    candidates = [name] if ext.lower() in _RUNNABLE_WINDOWS else [name + e for e in exts]
    if os.path.dirname(name):
        return next((c for c in candidates if _startable(c)), None)
    for folder in [d for d in os.environ.get("PATH", "").split(os.pathsep) if d]:
        for candidate in candidates:
            full = os.path.join(folder, candidate)
            if _startable(full):
                return full
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
