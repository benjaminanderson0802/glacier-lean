#!/usr/bin/env python3
"""Create a portable folder of pinned Python wheels and Glacier's guide."""
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


def _platform_tags(platform_name):
    if isinstance(platform_name, str):
        return [platform_name]
    return list(platform_name)


def download_command(requirements, destination, platform_name, python_version):
    tags = _platform_tags(platform_name)
    command = [sys.executable, "-m", "pip", "download", "--only-binary=:all:",
               "--requirement", str(requirements), "--dest", str(destination)]
    for tag in tags:
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
        command[0:3] = [pip, "download"]
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
    guide = repo_root / "docs" / "guide"
    sources = sorted(guide.glob("*.md"))
    if not sources:
        raise ValueError("No guide pages were found in docs/guide.")
    try:
        import markdown  # noqa: F401
        html_mode = True
    except ImportError:
        html_mode = False
    destination.mkdir(parents=True, exist_ok=True)
    if html_mode:
        for source in sources:
            name = "index.html" if source.name == "README.md" else source.with_suffix(".html").name
            _render_markdown(source, destination / name)
    else:
        for source in sources:
            shutil.copy2(source, destination / source.name)
    return html_mode


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _wheel_distribution(wheel):
    with zipfile.ZipFile(wheel) as archive:
        metadata_name = next((name for name in archive.namelist()
                              if name.endswith(".dist-info/METADATA")), None)
        if not metadata_name:
            raise ValueError("A downloaded wheel has no package metadata: " + wheel.name)
        metadata = email.message_from_bytes(archive.read(metadata_name))
    name = metadata.get("Name")
    version = metadata.get("Version")
    if not name or not version:
        raise ValueError("A downloaded wheel has incomplete package metadata: " + wheel.name)
    return name, version


def write_manifest(pack, metadata=None):
    files = []
    for path in sorted(p for p in pack.rglob("*") if p.is_file() and p.name != "MANIFEST.json"):
        files.append({"path": path.relative_to(pack).as_posix(), "sha256": _sha256(path),
                      "size_bytes": path.stat().st_size})
    manifest = {"format_version": 1, "files": files, "metadata": metadata or {}}
    (pack / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def zip_pack(pack, archive):
    archive = Path(archive)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
        for path in sorted(p for p in Path(pack).rglob("*") if p.is_file()):
            zipped.write(path, Path(pack).name + "/" + path.relative_to(pack).as_posix())


def _ollama_info(model):
    if not model:
        return None
    if not shutil.which("ollama"):
        raise RuntimeError("Ollama is not installed, so model size cannot be checked.")
    command = ["ollama", "list"]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    size = "not available because this model is not installed; model files are not bundled"
    if result.returncode == 0:
        for line in result.stdout.splitlines()[1:]:
            fields = line.split()
            if fields and fields[0] == model:
                size = "installed size: " + " ".join(fields[1:]) + "; this size is an estimate for the download"
                break
    return {"name": model, "pull_command": "ollama pull " + model, "size": size}


def build_pack(repo_root=ROOT, output=None, platform_name=LINUX_PLATFORMS,
               python_version="3.12", ollama_model=None, include_model=False):
    repo_root = Path(repo_root).resolve()
    output = Path(output or (repo_root / "offline-pack")).resolve()
    archive_output = output.suffix.lower() == ".zip"
    pack_dir = output.with_suffix("") if archive_output else output
    if pack_dir.exists():
        if pack_dir.is_dir():
            shutil.rmtree(pack_dir)
        else:
            pack_dir.unlink()
    pack_dir.mkdir(parents=True)
    wheels = pack_dir / "wheels"
    download_wheels(repo_root / "setup" / "requirements.txt", wheels,
                    platform_name, python_version)
    installed = sorted(_wheel_distribution(wheel) for wheel in wheels.glob("*.whl"))
    (pack_dir / "requirements.txt").write_text(
        "".join(name + "==" + version + "\n" for name, version in installed), encoding="utf-8")
    html_mode = _guide_files(repo_root, pack_dir / "docs")
    model = _ollama_info(ollama_model)
    if include_model:
        if not model:
            raise ValueError("Use --ollama-model NAME with --include-model.")
        if not shutil.which("ollama"):
            raise RuntimeError("Ollama is not installed; the model cannot be included.")
        model_dir = Path.home() / ".ollama" / "models"
        if not model_dir.is_dir():
            raise RuntimeError("Ollama model files were not found in the usual models folder.")
        if "not available because" in model["size"]:
            raise RuntimeError("The requested Ollama model is not installed, so there are no model files to include.")
        print("Copying Ollama model files. This may take a long time and use a lot of disk space.")
        shutil.copytree(model_dir, pack_dir / "ollama-models")
        model["included_folder"] = "ollama-models"
    readme = ["Glacier offline setup pack", "", "1. Copy this whole folder to the offline computer.",
              "2. Run install_pack.py with Python 3.12 installed.",
              "3. Keep MANIFEST.json with the files; it is used to check them before installation.", "",
              "The guide is " + ("HTML" if html_mode else "plain Markdown") + "."]
    if model:
        readme += ["", "Optional local model:", model["pull_command"],
                   "Approximate/available size: " + model["size"] + "."]
        if model.get("included_folder"):
            readme += ["Model files are included under " + model["included_folder"] +
                       ". Copy them into Ollama's models folder on the offline computer."]
    (pack_dir / "README.txt").write_text("\n".join(readme) + "\n", encoding="utf-8")
    tags = _platform_tags(platform_name)
    write_manifest(pack_dir, {"platform": tags[0] if len(tags) == 1 else tags,
                            "python_version": python_version,
                            "ollama_model": model})
    if archive_output:
        zip_pack(pack_dir, output)
        shutil.rmtree(pack_dir)
        print("Pack created at " + str(output))
        return output
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
    platform_tags = args.platform or list(LINUX_PLATFORMS)
    try:
        result = build_pack(output=args.output, platform_name=platform_tags,
                            python_version=args.python_version, ollama_model=args.ollama_model,
                            include_model=args.include_model)
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        print("Could not build the pack: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
