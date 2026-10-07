#!/usr/bin/env python3
"""Check and install a Glacier offline pack without contacting package indexes."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import platform
import shutil
import subprocess
import sys
import venv


def verify_manifest(pack):
    pack = Path(pack).resolve()
    manifest_path = pack / "MANIFEST.json"
    if not manifest_path.is_file():
        return ["MANIFEST.json is missing."]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ["MANIFEST.json cannot be read. The pack may be damaged."]
    problems = []
    entries = manifest.get("files")
    if not isinstance(entries, list):
        return ["The manifest has an invalid file list."]
    expected = set()
    for item in entries:
        relative = item.get("path", "") if isinstance(item, dict) else ""
        if not isinstance(relative, str):
            problems.append("The manifest contains an unsafe file path.")
            continue
        path_part = PurePosixPath(relative)
        if not relative or path_part.is_absolute() or ".." in path_part.parts:
            problems.append("The manifest contains an unsafe file path.")
            continue
        expected.add(path_part.as_posix())
        path = pack.joinpath(*path_part.parts)
        if not path.is_file():
            problems.append("A pack file is missing: " + relative)
            continue
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            problems.append("A pack file could not be read: " + relative)
            continue
        if digest != item.get("sha256"):
            problems.append("A pack file has changed: " + relative)
    actual = {p.relative_to(pack).as_posix() for p in pack.rglob("*")
              if p.is_file() and p.name != "MANIFEST.json"}
    for relative in sorted(actual - expected):
        problems.append("An unexpected file is in the pack: " + relative)
    return problems


def create_environment(destination):
    venv.EnvBuilder(with_pip=True).create(destination)


def _venv_python(destination):
    return destination / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")


def _check_tools(python):
    checks = [("Python", [str(python), "--version"]), ("uv", ["uv", "--version"]),
              ("Node.js", ["node", "--version"]), ("npm", ["npm", "--version"]),
              ("Git", ["git", "--version"]), ("GitHub CLI", ["gh", "--version"]),
              ("Codex", ["codex", "--version"]), ("Ollama", ["ollama", "--version"]),
              ("OpenCode", ["opencode", "--version"]), ("Gemini CLI", ["gemini", "--version"]),
              ("Docker", ["docker", "--version"]), ("Rust Cargo", ["cargo", "--version"]),
              ("ntfy", ["ntfy", "--help"])]
    for name, command in checks:
        executable = shutil.which(command[0]) if command[0] != str(python) else command[0]
        if not executable:
            print("Not found: " + name + ". You can install it later if you need it.")
            continue
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
        except (OSError, subprocess.SubprocessError):
            result = None
        if result and result.returncode == 0:
            first = next((line.strip() for line in (result.stdout + "\n" + result.stderr).splitlines()
                          if line.strip()), "ready")
            print("Ready: " + name + " — " + first)
        else:
            print("Not found: " + name + ". You can install it later if you need it.")
    module_checks = [
        ("agent-framework-core", "agent_framework"), ("DBOS", "dbos"), ("MCP", "mcp"),
        ("GitPython", "git"), ("FastAPI", "fastapi"), ("Uvicorn", "uvicorn"),
        ("WebSockets", "websockets"), ("pytest", "pytest"), ("HTTPX", "httpx"),
        ("ACP", "acp"), ("MarkItDown", "markitdown"), ("Docling", "docling"),
        ("sqlite-vec", "sqlite_vec"), ("Apprise", "apprise"),
        ("Agent Framework AG-UI", "agent_framework_ag_ui"),
    ]
    for label, module in module_checks:
        try:
            result = subprocess.run([str(python), "-c", "import " + module], capture_output=True,
                                    text=True, timeout=10, check=False)
        except (OSError, subprocess.SubprocessError):
            result = None
        if result and result.returncode == 0:
            print("Ready: Python package " + label)
        else:
            print("Not found: Python package " + label + ". You can install it later if you need it.")
    for label, binary in [("Bifrost", "bifrost"), ("Chromium", "chromium"),
                          ("Rust", "rustc")]:
        print(("Ready: " if shutil.which(binary) else "Not found: ") + label +
              ("" if shutil.which(binary) else ". You can install it later if you need it."))


def install(pack, destination):
    pack = Path(pack).resolve()
    destination = Path(destination).resolve()
    problems = verify_manifest(pack)
    if problems:
        print("This pack did not pass its file check. Nothing was installed.")
        for problem in problems:
            print("- " + problem)
        return False
    wheels = pack / "wheels"
    wheel_files = list(wheels.glob("*.whl")) if wheels.is_dir() else []
    if not wheel_files:
        print("This pack has no Python packages to install.")
        return False
    requirements = pack / "requirements.txt"
    if destination.exists():
        print("The install folder already exists: " + str(destination))
        print("Choose a new, empty folder and try again.")
        return False
    print("The pack files are okay. Creating the Python environment now.")
    try:
        create_environment(destination)
        python = _venv_python(destination)
        command = [str(python), "-m", "pip", "install", "--no-index", "--find-links",
                   str(wheels)]
        if requirements.is_file():
            command += ["-r", str(requirements)]
        else:
            command += [wheel.name for wheel in wheel_files]
        subprocess.run(command, check=True)
    except (OSError, subprocess.CalledProcessError, venv.Error) as exc:
        print("Installation could not finish: " + str(exc))
        return False
    print("The Python packages are installed.")
    _check_tools(_venv_python(destination))
    print("Setup is complete. Your offline guide is in the docs folder in the pack.")
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description="Install a checked Glacier pack without internet.")
    parser.add_argument("pack", nargs="?", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--destination", type=Path, default=Path("Glacier-offline"))
    args = parser.parse_args(argv)
    return 0 if install(args.pack, args.destination) else 1


if __name__ == "__main__":
    raise SystemExit(main())
