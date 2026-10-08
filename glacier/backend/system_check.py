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
# The default is Apache-2.0 and reached 8/10 in the local-model benchmark, including
# when run sequentially in low-resource mode (evidence/PH8.5-granite-light-bench.md).
RECOMMENDED_MODELS = {
    "low": DEFAULT_MODEL,
    "standard": DEFAULT_MODEL,
}
INSTALLED_MODEL_ORDER = (
    "granite3.3:2b",
    "qwen3:0.6b",
    "qwen3:1.7b",
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


def _ollama_api_models():
    """Models from the running Ollama server's own API (None when it does not answer).

    More reliable than the command line: a PC can have several ollama.exe copies on PATH and
    the first one may not run (seen on a real PC: a broken winget link ahead of the real install).
    """
    import urllib.request
    url = os.environ.get("GLACIER_OLLAMA_URL", "http://localhost:11434").rstrip("/") + "/api/tags"
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(url, timeout=1) as response:
            payload = json.loads(response.read(2_000_000))
    except Exception:
        return None
    models = payload.get("models") if isinstance(payload, dict) else None
    if not isinstance(models, list):
        return None
    return [str(m.get("name")) for m in models if isinstance(m, dict) and m.get("name")]


def _ollama_models():
    from_api = _ollama_api_models()
    if from_api is not None:
        return from_api
    path = shell_commands.which("ollama")
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
    available_models = machine.get("ollama_models") or []
    installed = [m for m in available_models
                 if "embed" not in m.lower() and "minilm" not in m.lower()]
    # 1) an evaluated model already installed; 2) any other chat model the user installed (smallest first, no
    # download needed); 3) the recommended default for this mode.
    # Glacier's evaluated default wins when present; otherwise prefer the smallest
    # evaluated model, then another installed chat model.
    # Prefer the smallest evaluated model that is already available; Granite is
    # still the default when Ollama has no chat models installed.
    model = next((name for name in INSTALLED_MODEL_ORDER if name in installed), None)
    if model is None and installed:
        def size(name):
            match = re.search(r"(?:^|[-:])(\d+(?:\.\d+)?)\s*([bm])(?:\b|$)", name.lower())
            return float("inf") if not match else float(match.group(1)) * (1_000 if match.group(2) == "b" else 1)
        model = min(enumerate(installed), key=lambda item: (size(item[1]), item[0]))[1]
    # Keep the standard default visible on a fresh install. The starter response
    # marks it as needing a download until Ollama reports it as installed.
    model = model or (RECOMMENDED_MODELS[mode] if not installed else None)
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
        path = shell_commands.which(binary)
        version = _run([path, *args]) if path else ""
        tools[name] = {"found": bool(path and version), "version": version}
    models = _ollama_models()
    if not tools["ollama"]["found"] and _ollama_api_models() is not None:
        # The server is running even if the ollama command on PATH could not be started.
        tools["ollama"] = {"found": True, "version": "running (local API)"}
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


def _recommended_light():
    """Recommendation from hardware and installed models only (no tool probes).

    Used at start-up so a slow or broken tool on PATH can never stop the engine starting.
    """
    if _check_cache is not None:
        return dict(_check_cache["recommended"])
    cores, memory_gb, disk_free_gb = _machine_stats()
    return recommend({"cpu_cores": cores, "memory_gb": memory_gb, "disk_free_gb": disk_free_gb,
                      "ollama_models": _ollama_models()})


def effective_settings(include_ask_route: bool = False):
    result = _recommended_light()
    settings_path = Path(os.environ.get("GLACIER_HOME", "data")) / "settings.json"
    try:
        saved = json.loads(settings_path.read_text(encoding="utf-8"))
        if saved.get("mode") in {"low", "standard"}:
            result["mode"] = saved["mode"]
        if isinstance(saved.get("local_model"), str) and saved["local_model"].strip():
            saved_model = saved["local_model"].strip()
            installed = check_system().get("ollama_models") or []
            if saved_model in installed:
                result["local_model"] = saved_model
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
    if include_ask_route:
        import routes.assistant_chat as assistant_chat
        route, reason = assistant_chat.ask_route()
        result["ask_route"] = route or "unavailable"
        result["ask_route_reason"] = reason
        saved = assistant_chat._saved_settings()
        result["ask_engine"] = saved.get("ask_engine", "codex")
        result["ask_engines"] = assistant_chat.available_engines()
        result["ask_remember_previous_chats"] = assistant_chat.ask_context.remember_chats()
    return result


def default_local_model() -> str:
    """The model local steps use when a step names none: GLACIER_LOCAL_MODEL, else the saved or recommended choice."""
    configured = os.environ.get("GLACIER_LOCAL_MODEL", "").strip()
    if configured:
        return configured
    try:
        # Prefer a persisted owner selection; otherwise the common default is
        # the same model as the fallback in nodes/local_ai.py.
        return str(effective_settings().get("local_model") or DEFAULT_MODEL)
    except Exception:  # a failing hardware check must never stop a step
        return DEFAULT_MODEL
