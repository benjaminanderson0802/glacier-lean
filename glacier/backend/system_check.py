"""Cross-platform hardware and local tool checks for first-run setup."""
import os
import platform
import re
import shutil
import subprocess
import time
import shell_commands
import json
from pathlib import Path


DEFAULT_MODEL = "granite3.3:2b"
# All entries are small, instruct-tuned models under OSI-approved licenses (evidence/live/model_choice.md).
# Low-resource mode must fit a modest PC: qwen3:0.6b peaks around 1 GiB, granite3.3:2b around 5 GiB.
RECOMMENDED_MODELS = {
    "low": "qwen3:0.6b",
    "standard": DEFAULT_MODEL,
}
INSTALLED_MODEL_ORDER = (
    "qwen3:0.6b",
    "qwen3:1.7b",
    "granite3.3:2b",
    "smollm2:1.7b",
)
CACHE_SECONDS = 60
_check_cache = None
_check_cache_at = 0.0
_check_cache_key = None
TOOL_COMMANDS = {
    "codex": ("codex", ["--version"]),
    "ollama": ("ollama", ["--version"]),
    "git": ("git", ["--version"]),
    "python": ("python", ["--version"]),
    "node": ("node", ["--version"]),
    "tesseract": ("tesseract", ["--version"]),
}


def _machine_stats():
    """Return logical cores, RAM in GiB and free disk space in GiB."""
    cores = os.cpu_count() or 1
    memory_gb = None
    if platform.system() == "Windows":
        try:
            import ctypes
            class MemoryStatus(ctypes.Structure):
                _fields_ = [("length", ctypes.c_ulong), ("memory_load", ctypes.c_ulong),
                            ("total_phys", ctypes.c_ulonglong), ("avail_phys", ctypes.c_ulonglong),
                            ("total_page", ctypes.c_ulonglong), ("avail_page", ctypes.c_ulonglong),
                            ("total_virtual", ctypes.c_ulonglong), ("avail_virtual", ctypes.c_ulonglong),
                            ("avail_extended", ctypes.c_ulonglong)]
            status = MemoryStatus()
            status.length = ctypes.sizeof(status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                memory_gb = status.total_phys / (1024 ** 3)
        except (AttributeError, OSError):
            pass
    elif os.name == "posix":
        try:
            page_size = os.sysconf("SC_PAGE_SIZE")
            page_count = os.sysconf("SC_PHYS_PAGES")
            if page_size > 0 and page_count > 0:
                memory_gb = page_size * page_count / (1024 ** 3)
        except (AttributeError, OSError, ValueError):
            pass
    try:
        disk_path = os.environ.get("GLACIER_HOME") or os.getcwd()
        disk_free_gb = shutil.disk_usage(disk_path).free / (1024 ** 3)
    except OSError:
        disk_free_gb = 0.0
    return cores, round(memory_gb, 1) if memory_gb is not None else None, round(disk_free_gb, 1)


def _run(command, timeout=2, first_line=True):
    try:
        if command and isinstance(command[0], str):
            command = shell_commands.executable_invocation(command[0], *command[1:])
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout,
                                check=False, shell=False)
    except (OSError, subprocess.SubprocessError):
        return ""
    if result.returncode != 0:
        return ""
    output = (result.stdout + "\n" + result.stderr).strip()
    if first_line:
        return next((line.strip() for line in output.splitlines() if line.strip()), "")
    return output


def _ollama_models():
    path = shutil.which("ollama")
    if not path:
        return []
    output = _run([path, "list"], first_line=False)
    models = []
    for line in output.splitlines()[1:]:
        name = line.split()[0] if line.split() else ""
        if name:
            models.append(name)
    return models


def recommend(machine):
    """Choose usable local settings from detected hardware and installed models."""
    cores = int(machine.get("cpu_cores") or 1)
    raw_memory = machine.get("memory_gb")
    memory = float(raw_memory) if raw_memory is not None else None
    low = (memory is not None and memory <= 8) or cores <= 4
    mode = "low" if low else "standard"
    installed = [m for m in (machine.get("ollama_models") or [])
                 if "embed" not in m.lower() and "minilm" not in m.lower()]
    # 1) an evaluated model already installed; 2) any other chat model the user installed (smallest first, no
    # download needed); 3) the recommended default for this mode.
    model = next((name for name in INSTALLED_MODEL_ORDER if name in installed), None)
    if model is None and installed:
        def size(name):
            match = re.search(r"(?:^|[-:])(\d+(?:\.\d+)?)\s*([bm])(?:\b|$)", name.lower())
            return float("inf") if not match else float(match.group(1)) * (1_000 if match.group(2) == "b" else 1)
        model = min(enumerate(installed), key=lambda item: (size(item[1]), item[0]))[1]
    model = model or RECOMMENDED_MODELS[mode]
    return {"mode": mode, "local_model": model,
            "max_parallel_runs": 1 if low else min(4, max(1, cores // 2))}


def check_system():
    global _check_cache, _check_cache_at, _check_cache_key
    now = time.monotonic()
    cache_key = (os.environ.get("PATH"), os.environ.get("GLACIER_HOME"))
    if (_check_cache is not None and cache_key == _check_cache_key
            and now - _check_cache_at < CACHE_SECONDS):
        return _check_cache
    cores, memory_gb, disk_free_gb = _machine_stats()
    tools = {}
    for name, (binary, args) in TOOL_COMMANDS.items():
        path = shutil.which(binary)
        version = _run([path, *args]) if path else ""
        tools[name] = {"found": bool(path and version), "version": version}
    models = _ollama_models()
    machine = {"cpu_cores": cores, "memory_gb": memory_gb, "disk_free_gb": disk_free_gb,
               "ollama_models": models}
    messages = []
    if not tools["codex"]["found"]:
        messages.append("Codex is not installed. You can still use a local model if Ollama is available.")
    if not tools["ollama"]["found"]:
        messages.append("Ollama is not installed. Install it to use AI models running on this computer.")
    elif not models:
        messages.append("Ollama is ready, but no models are installed yet. Download a small model to get started.")
    if memory_gb and memory_gb <= 8:
        messages.append("This computer has limited memory, so Glacier recommends one run at a time and a small model.")
    if memory_gb is None:
        messages.append("Computer memory is unknown, so Glacier cannot check whether a smaller model is recommended.")
    if disk_free_gb and disk_free_gb < 10:
        messages.append("Free up some disk space before downloading a local model.")
    machine["tools"] = tools
    machine["recommended"] = recommend(machine)
    machine["messages"] = messages
    _check_cache = machine
    _check_cache_at = now
    _check_cache_key = cache_key
    return machine


def clear_cache():
    """Clear cached hardware discovery (primarily for isolated checks)."""
    global _check_cache, _check_cache_at, _check_cache_key
    _check_cache = None
    _check_cache_at = 0.0
    _check_cache_key = None


def effective_settings():
    result = dict(check_system()["recommended"])
    settings_path = Path(os.environ.get("GLACIER_HOME", "data")) / "settings.json"
    try:
        saved = json.loads(settings_path.read_text(encoding="utf-8"))
        if saved.get("mode") in {"low", "standard"}:
            result["mode"] = saved["mode"]
        if isinstance(saved.get("local_model"), str) and saved["local_model"].strip():
            result["local_model"] = saved["local_model"].strip()
        if isinstance(saved.get("max_parallel_runs"), int) and saved["max_parallel_runs"] > 0:
            result["max_parallel_runs"] = saved["max_parallel_runs"]
    except (OSError, ValueError, TypeError):
        pass
    local_model = os.environ.get("GLACIER_LOCAL_MODEL", "").strip()
    if local_model:
        result["local_model"] = local_model
    max_runs = os.environ.get("GLACIER_MAX_PARALLEL_RUNS", "").strip()
    if max_runs:
        try:
            result["max_parallel_runs"] = max(1, int(max_runs))
        except ValueError:
            pass
    return result


def default_local_model() -> str:
    """The model local steps use when a step names none: GLACIER_LOCAL_MODEL, else the saved or recommended choice."""
    configured = os.environ.get("GLACIER_LOCAL_MODEL", "").strip()
    if configured:
        return configured
    try:
        return str(effective_settings().get("local_model") or "qwen3:0.6b")
    except Exception:  # a failing hardware check must never stop a step
        return "qwen3:0.6b"
