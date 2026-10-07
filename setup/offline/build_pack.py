#!/usr/bin/env python3
"""Create a portable folder of pinned Python wheels, Glacier source, and guides."""
import argparse
import hashlib
import html
import email
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[2]
LINUX_PLATFORMS = ("manylinux_2_28_x86_64", "manylinux_2_27_x86_64",
                   "manylinux_2_17_x86_64", "manylinux2014_x86_64")
PLATFORMS = ("win_amd64", *LINUX_PLATFORMS, "macosx_11_0_x86_64", "macosx_11_0_arm64")
IGNORED_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}


def _platform_tags(platform_name):
    return [platform_name] if isinstance(platform_name, str) else list(platform_name)


def download_command(requirements, destination, platform_name, python_version):
    command = [sys.executable, "-m", "pip", "download", "--only-binary=:all:",
               "--requirement", str(requirements), "--dest", str(destination)]
    for tag in _platform_tags(platform_name):
        command.extend(["--platform", tag])
    command += ["--python-version", python_version, "--implementation", "cp",
                "--abi", "cp" + python_version.replace(".", "")]
    return command


def download_wheels(requirements, destination, platform_name, python_version):
    destination.mkdir(parents=True, exist_ok=True)
    command = download_command(requirements, destination, platform_name, python_version)
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"],
                       capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        pip = shutil.which("pip3") or shutil.which("pip")
        if not pip:
            raise RuntimeError("Pip is missing. Install Python with pip on the connected computer.")
        command = [pip, "download", *command[4:]]
    print("Downloading the pinned Python packages. This needs an internet connection.")
    subprocess.run(command, check=True)


def _render_markdown(source, destination):
    text = source.read_text(encoding="utf-8")
    try:
        import markdown
        body = markdown.markdown(text, extensions=["tables", "fenced_code"])
    except ImportError:
        body = "<pre>" + html.escape(text) + "</pre>"
    title = source.stem.replace("-", " ").title()
    destination.write_text("<!doctype html><html><head><meta charset=\"utf-8\"><title>" +
                           html.escape(title) + "</title></head><body>" + body +
                           "</body></html>\n", encoding="utf-8")


def _guide_files(repo_root, destination):
    sources = sorted((repo_root / "docs" / "guide").glob("*.md"))
    if not sources:
        raise ValueError("No guide pages were found in docs/guide.")
    try:
        import markdown  # noqa: F401
        html_mode = True
    except ImportError:
        html_mode = False
    destination.mkdir(parents=True, exist_ok=True)
    for source in sources:
        if html_mode:
            name = "index.html" if source.name == "README.md" else source.with_suffix(".html").name
            _render_markdown(source, destination / name)
        else:
            shutil.copy2(source, destination / source.name)
    return html_mode


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_sha256(pack):
    return _sha256(Path(pack) / "MANIFEST.json")


def _wheel_distribution(wheel):
    with zipfile.ZipFile(wheel) as archive:
        metadata_name = next((name for name in archive.namelist()
                              if name.endswith(".dist-info/METADATA")), None)
        if not metadata_name:
            raise ValueError("A downloaded wheel has no package metadata: " + wheel.name)
        metadata = email.message_from_bytes(archive.read(metadata_name))
    name, version = metadata.get("Name"), metadata.get("Version")
    if not name or not version:
        raise ValueError("A downloaded wheel has incomplete package metadata: " + wheel.name)
    return name, version


def write_manifest(pack, metadata=None):
    pack = Path(pack)
    files = []
    for path in sorted(p for p in pack.rglob("*") if p.is_file() and p.name != "MANIFEST.json"):
        if path.name in IGNORED_NAMES or path.name.startswith("._"):
            continue
        files.append({"path": path.relative_to(pack).as_posix(), "sha256": _sha256(path),
                      "size_bytes": path.stat().st_size})
    manifest = {"format_version": 1, "files": files, "metadata": metadata or {}}
    (pack / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def zip_pack(pack, archive):
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
        for path in sorted(p for p in Path(pack).rglob("*") if p.is_file()):
            zipped.write(path, Path(pack).name + "/" + path.relative_to(pack).as_posix())


def _ollama_info(model):
    if not model:
        return None
    if not shutil.which("ollama"):
        return {"name": model, "pull_command": "ollama pull " + model,
                "size": "not available because Ollama is not installed; model files are not bundled"}
    result = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=False)
    size = "not available because this model is not installed; model files are not bundled"
    if result.returncode == 0:
        for line in result.stdout.splitlines()[1:]:
            fields = line.split()
            if fields and fields[0] == model:
                size = "installed size: " + " ".join(fields[1:]) + "; this size is an estimate for the download"
                break
    return {"name": model, "pull_command": "ollama pull " + model, "size": size}


def _source_archive(repo_root, destination):
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / "glacier-source.tar"
    try:
        with archive.open("wb") as stream:
            subprocess.run(["git", "-C", str(repo_root), "archive", "--format=tar", "HEAD"],
                           check=True, stdout=stream, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.CalledProcessError):
        archive.unlink(missing_ok=True)
        print("Glacier source was not available as a Git archive; the setup pack can still be used.")


def build_pack(repo_root=ROOT, output=None, platform_name=LINUX_PLATFORMS,
               python_version="3.12", ollama_model=None, include_model=False):
    repo_root = Path(repo_root).resolve()
    output = Path(output or (repo_root / "offline-pack")).resolve()
    archive_output = output.suffix.lower() == ".zip"
    pack_dir = output.with_suffix("") if archive_output else output
    if pack_dir.exists():
        shutil.rmtree(pack_dir) if pack_dir.is_dir() else pack_dir.unlink()
    pack_dir.mkdir(parents=True)
    wheels = pack_dir / "wheels"
    download_wheels(repo_root / "setup" / "requirements.txt", wheels, platform_name, python_version)
    installed = sorted(_wheel_distribution(wheel) for wheel in wheels.glob("*.whl"))
    (pack_dir / "requirements.txt").write_text(
        "".join(name + "==" + version + "\n" for name, version in installed), encoding="utf-8")
    _guide_files(repo_root, pack_dir / "docs")
    _source_archive(repo_root, pack_dir / "source")
    shutil.copy2(Path(__file__).resolve(), pack_dir / "install_pack.py")
    model = _ollama_info(ollama_model)
    if include_model:
        if not model:
            raise ValueError("Use --ollama-model NAME with --include-model.")
        if not shutil.which("ollama"):
            raise RuntimeError("Ollama is not installed; the model cannot be included.")
        model_dir = Path.home() / ".ollama" / "models"
        if not model_dir.is_dir() or "not available because" in model["size"]:
            raise RuntimeError("The requested Ollama model is not installed in the usual models folder.")
        print("Copying the installed Ollama model files. This may take a long time and use a lot of disk space.")
        shutil.copytree(model_dir, pack_dir / "ollama-models")
        model["included_folder"] = "ollama-models"
        model["included_scope"] = "all installed Ollama model blobs"
    (pack_dir / "README.txt").write_text(
        "Glacier offline setup pack\n\n"
        "1. Copy this whole folder to the offline computer.\n"
        "2. Run install_pack.py with Python 3.12 installed.\n"
        "3. Keep MANIFEST.json and MANIFEST.sha256 with the files.\n"
        "   The installer prints the MANIFEST SHA-256 before it checks the pack.\n\n"
        "The guide is available in the docs folder.\n"
        + (("\nOptional model: " + model["name"] + "\n" + model["pull_command"] +
            "\nApproximate size: " + model["size"] + "\n") if model else ""), encoding="utf-8")
    tags = _platform_tags(platform_name)
    write_manifest(pack_dir, {"platform": tags[0] if len(tags) == 1 else tags,
                              "python_version": python_version, "ollama_model": model})
    # README is covered by the manifest. The separate checksum file avoids a
    # self-referential manifest while giving the installer a stable digest.
    digest = manifest_sha256(pack_dir)
    (pack_dir / "MANIFEST.sha256").write_text(digest + "\n", encoding="ascii")
    if archive_output:
        zip_pack(pack_dir, output)
        shutil.rmtree(pack_dir)
        print("MANIFEST SHA-256: " + digest)
        print("Pack created at " + str(output))
        return output
    print("MANIFEST SHA-256: " + digest)
    print("Pack created at " + str(pack_dir))
    return pack_dir


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build a Glacier pack for an offline computer.")
    parser.add_argument("--platform", choices=PLATFORMS, action="append",
                        help="Target platform tag; repeat to include more compatible tags. Defaults to common Linux tags.")
    parser.add_argument("--python-version", default="3.12")
    parser.add_argument("--output", type=Path, default=ROOT / "offline-pack")
    parser.add_argument("--ollama-model")
    parser.add_argument("--include-model", action="store_true")
    args = parser.parse_args(argv)
    try:
        build_pack(output=args.output, platform_name=args.platform or list(LINUX_PLATFORMS),
                   python_version=args.python_version, ollama_model=args.ollama_model,
                   include_model=args.include_model)
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        print("Could not build the pack: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
