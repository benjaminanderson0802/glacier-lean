"""Cross-platform hardware and local tool checks for first-run setup."""
import os
import platform
import re
import shutil
import subprocess


DEFAULT_MODEL = "qwen3:0.6b"
TOOL_COMMANDS = {
    "codex": ("codex", ["--version"]),
    "ollama": ("ollama", ["--version"]),
    "git": ("git", ["--version"]),
    "python": ("python", ["--version"]),
    "node": ("node", ["--version"]),
}


def _machine_stats():
    """Return logical cores, RAM in GiB and free disk space in GiB."""
    cores = os.cpu_count() or 1
    memory_gb = 0.0
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
    else:
        try:
            with open("/proc/meminfo", encoding="ascii") as stream:
                match = re.search(r"^MemTotal:\s+(\d+)", stream.read(), re.MULTILINE)
            if match:
                memory_gb = int(match.group(1)) / (1024 ** 2)
        except OSError:
            pass
    try:
        disk_free_gb = shutil.disk_usage(os.getcwd()).free / (1024 ** 3)
    except OSError:
        disk_free_gb = 0.0
    return cores, round(memory_gb, 1), round(disk_free_gb, 1)


def _run(command, timeout=2, first_line=True):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout,
                                check=False, shell=False)
    except (OSError, subprocess.SubprocessError):
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
    memory = float(machine.get("memory_gb") or 0)
    models = list(machine.get("ollama_models") or [])
    low = memory <= 8 or cores <= 4
    def model_size(model):
        match = re.search(r"(?:^|[-:])(\d+(?:\.\d+)?)\s*([bm])(?:\b|$)", model.lower())
        if not match:
            return float("inf")
        return float(match.group(1)) * (1_000 if match.group(2) == "b" else 1)

    model = min(enumerate(models), key=lambda item: (model_size(item[1]), item[0]))[1] if models else DEFAULT_MODEL
    return {"mode": "low" if low else "standard", "local_model": model,
            "max_parallel_runs": 1 if low else min(4, max(1, cores // 2))}


def check_system():
    cores, memory_gb, disk_free_gb = _machine_stats()
    tools = {}
    for name, (binary, args) in TOOL_COMMANDS.items():
        path = shutil.which(binary)
        version = _run([path, *args]) if path else ""
        tools[name] = {"found": bool(path), "version": version}
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
    if disk_free_gb and disk_free_gb < 10:
        messages.append("Free up some disk space before downloading a local model.")
    machine["tools"] = tools
    machine["recommended"] = recommend(machine)
    machine["messages"] = messages
    return machine


def effective_settings():
    result = check_system()["recommended"]
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
