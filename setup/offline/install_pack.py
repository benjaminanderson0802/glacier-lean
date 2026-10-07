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
import tarfile
import venv

IGNORED_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}


def _ignored(path):
    return path.name in IGNORED_NAMES or path.name.startswith("._")


def verify_manifest(pack):
    pack = Path(pack).resolve()
    manifest_path = pack / "MANIFEST.json"
    if not manifest_path.is_file():
        return ["MANIFEST.json is missing."]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ["MANIFEST.json cannot be read. The pack may be damaged."]
    entries = manifest.get("files") if isinstance(manifest, dict) else None
    if not isinstance(entries, list):
        return ["The manifest has an invalid file list."]
    problems, expected = [], set()
    for item in entries:
        relative = item.get("path", "") if isinstance(item, dict) else ""
        if (not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative):
            problems.append("The manifest contains an unsafe file path.")
            continue
        path_part = PurePosixPath(relative)
        if path_part.is_absolute() or ".." in path_part.parts or "." in path_part.parts:
            problems.append("The manifest contains an unsafe file path.")
            continue
        path = pack.joinpath(*path_part.parts).resolve()
        try:
            path.relative_to(pack)
        except ValueError:
            problems.append("The manifest contains an unsafe file path.")
            continue
        if relative in expected:
            problems.append("The manifest lists a file more than once: " + relative)
            continue
        expected.add(relative)
        if _ignored(path):
            continue
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
              if p.is_file() and p.name not in {"MANIFEST.json", "MANIFEST.sha256"}
              and not _ignored(p)}
    for relative in sorted(actual - expected):
        problems.append("An unexpected file is in the pack: " + relative)
    return problems


def manifest_sha256(pack):
    digest = hashlib.sha256()
    with (Path(pack) / "MANIFEST.json").open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _platform_matches(metadata):
    expected = metadata.get("platform")
    tags = expected if isinstance(expected, list) else [expected]
    system = platform.system()
    machine = platform.machine().lower()
    if system == "Windows":
        actual = "win_amd64" if machine in ("amd64", "x86_64") else "win_" + machine
    elif system == "Linux":
        actual = "manylinux2014_x86_64" if machine in ("amd64", "x86_64") else "linux_" + machine
    elif system == "Darwin":
        actual = "macosx_11_0_arm64" if machine in ("arm64", "aarch64") else "macosx_11_0_x86_64"
    else:
        actual = system + "_" + machine
    compatible = {actual}
    if system == "Linux" and machine in ("amd64", "x86_64"):
        compatible.update({"manylinux2014_x86_64", "manylinux_2_17_x86_64",
                           "manylinux_2_28_x86_64", "manylinux_2_27_x86_64"})
    if system == "Darwin":
        compatible.add("macosx_11_0_arm64" if machine in ("arm64", "aarch64") else "macosx_11_0_x86_64")
    return bool(compatible.intersection(tags))


def _check_compatibility(metadata):
    wanted = str(metadata.get("python_version", ""))
    current = str(sys.version_info[0]) + "." + str(sys.version_info[1])
    if wanted and wanted != current:
        print("This pack needs Python " + wanted + ". Install that version and try again.")
        return False
    if not _platform_matches(metadata):
        expected = metadata.get("platform")
        if isinstance(expected, list):
            expected = expected[0] if expected else "the platform listed in the pack"
        if expected == "win_amd64":
            description = "Windows 64-bit"
        elif str(expected).startswith("manylinux"):
            description = "Linux 64-bit"
        elif str(expected).startswith("macosx"):
            description = "macOS"
        else:
            description = str(expected or "the platform listed in the pack")
        print("This pack needs Python " + (wanted or "the listed version") + " on " + description + ".")
        return False
    return True


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
        if command[0] != str(python) and not shutil.which(command[0]):
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
    modules = [("agent-framework-core", "agent_framework"), ("DBOS", "dbos"), ("MCP", "mcp"),
               ("GitPython", "git"), ("FastAPI", "fastapi"), ("Uvicorn", "uvicorn"),
               ("WebSockets", "websockets"), ("pytest", "pytest"), ("HTTPX", "httpx"),
               ("ACP", "acp"), ("MarkItDown", "markitdown"), ("sqlite-vec", "sqlite_vec"),
               ("Apprise", "apprise"), ("PyYAML", "yaml"), ("JSON Schema", "jsonschema"),
               ("Keyring", "keyring")]
    for label, module in modules:
        try:
            result = subprocess.run([str(python), "-c", "import " + module], capture_output=True,
                                    text=True, timeout=10, check=False)
        except (OSError, subprocess.SubprocessError):
            result = None
        print(("Ready: Python package " if result and result.returncode == 0 else
               "Not found: Python package " + label + ". You can install it later if you need it."))


def _install_source(pack, destination):
    archive = pack / "source" / "glacier-source.tar"
    if not archive.is_file():
        return True
    source = destination / "source"
    source.mkdir()
    try:
        with tarfile.open(archive, "r:") as tar:
            root = source.resolve()
            for member in tar.getmembers():
                target = (source / member.name).resolve()
                try:
                    target.relative_to(root)
                except ValueError:
                    raise ValueError("The source archive contains an unsafe path.")
            tar.extractall(source, filter="data")
    except (OSError, tarfile.TarError, ValueError) as exc:
        print("Glacier's source files could not be copied: " + str(exc))
        return False
    return True


def install(pack, destination, expected_manifest_sha256=None):
    pack, destination = Path(pack).resolve(), Path(destination).resolve()
    try:
        digest = manifest_sha256(pack)
    except OSError:
        print("MANIFEST.json is missing or cannot be read. Nothing was installed.")
        return False
    print("MANIFEST SHA-256: " + digest)
    checksum_file = pack / "MANIFEST.sha256"
    if checksum_file.exists():
        try:
            saved_digest = checksum_file.read_text(encoding="ascii").strip()
        except OSError:
            print("MANIFEST.sha256 cannot be read. Nothing was installed.")
            return False
        if saved_digest.lower() != digest.lower():
            print("MANIFEST.json does not match MANIFEST.sha256. The pack may have changed.")
            return False
    if expected_manifest_sha256 and digest.lower() != expected_manifest_sha256.strip().lower():
        print("The MANIFEST SHA-256 does not match the value you were given. The pack may have changed.")
        return False
    problems = verify_manifest(pack)
    if problems:
        print("This pack did not pass its file check. Nothing was installed.")
        for problem in problems:
            print("- " + problem)
        return False
    try:
        manifest = json.loads((pack / "MANIFEST.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print("MANIFEST.json cannot be read. Nothing was installed.")
        return False
    if not _check_compatibility(manifest.get("metadata", {})):
        return False
    files = [item["path"] for item in manifest["files"] if item["path"].startswith("wheels/")
             and item["path"].endswith(".whl")]
    if not files:
        print("This pack has no Python packages to install.")
        return False
    if destination.exists():
        print("The install folder already exists: " + str(destination))
        print("Choose a new, empty folder and try again.")
        return False
    print("The pack files are okay. Creating the Python environment now.")
    try:
        create_environment(destination)
        if not _install_source(pack, destination):
            return False
        python = _venv_python(destination)
        command = [str(python), "-m", "pip", "install", "--no-index", "--find-links", str(pack / "wheels")]
        command.extend(str(pack / relative) for relative in files)
        subprocess.run(command, check=True)
    except (OSError, subprocess.CalledProcessError, RuntimeError) as exc:
        print("Installation could not finish: " + str(exc))
        return False
    print("The Python packages are installed.")
    _check_tools(_venv_python(destination))
    if (destination / "source").is_dir():
        print("Setup is complete. Glacier's source is in the source folder and the offline guide is in docs.")
    else:
        print("Setup is complete. The offline guide is in the docs folder.")
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description="Install a checked Glacier pack without internet.")
    parser.add_argument("pack", nargs="?", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--destination", type=Path, default=Path("Glacier-offline"))
    parser.add_argument("--manifest-sha256", help="Check against the SHA-256 shared by the pack builder.")
    args = parser.parse_args(argv)
    return 0 if install(args.pack, args.destination, args.manifest_sha256) else 1


if __name__ == "__main__":
    raise SystemExit(main())
