#!/usr/bin/env python3
"""Build a private CPython runtime with the pinned Glacier backend wheels."""
import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile


ROOT = Path(__file__).resolve().parents[2]
RELEASE = "20261003"
VERSION = "3.12.15"
ASSETS = {
    "x86_64-unknown-linux-gnu": {
        "archive": f"cpython-{VERSION}+{RELEASE}-x86_64-unknown-linux-gnu-install_only.tar.gz",
        "sha256": "f937814031eab4698ca6d07ec606ede1825768f3f3e99af76d9db3900bee03c5",
        "wheels": ("manylinux_2_28_x86_64", "manylinux_2_27_x86_64",
                    "manylinux_2_17_x86_64", "manylinux2014_x86_64"),
    },
    "x86_64-pc-windows-msvc": {
        "archive": f"cpython-{VERSION}+{RELEASE}-x86_64-pc-windows-msvc-install_only.tar.gz",
        "sha256": "4b6f0beebbb695a0f3ea237b8c3eaa5bd424f47a7bc25b2fbe3a43390c770f08",
        "wheels": "win_amd64",
    },
    "aarch64-apple-darwin": {
        "archive": f"cpython-{VERSION}+{RELEASE}-aarch64-apple-darwin-install_only.tar.gz",
        "sha256": "316a463172740e71d8dca1f2730784e325f3f720941137b5d674d5801a632213",
        "wheels": "macosx_11_0_arm64",
    },
}
BASE_URL = f"https://github.com/astral-sh/python-build-standalone/releases/download/{RELEASE}/"


def verify_sha256(archive, expected):
    digest = hashlib.sha256()
    with Path(archive).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual.lower() != expected.lower():
        raise ValueError(f"Runtime SHA-256 mismatch: expected {expected}, received {actual}")
    return actual


def _safe_target(root, member):
    target = (root / member).resolve()
    if target != root and root not in target.parents:
        raise ValueError("Runtime archive contains a path outside its destination")
    return target


def extract_runtime(archive, destination, strip_prefix="python"):
    """Safely extract supported standalone archives, removing their top folder."""
    archive, destination = Path(archive), Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    if tarfile.is_tarfile(archive):
        with tarfile.open(archive, "r:*") as bundle:
            for member in bundle.getmembers():
                relative = Path(member.name)
                if relative.is_absolute() or ".." in relative.parts:
                    raise ValueError("Runtime archive contains an unsafe path")
                parts = relative.parts[1:] if relative.parts and relative.parts[0] == strip_prefix else relative.parts
                if not parts:
                    continue
                target = _safe_target(destination, Path(*parts))
                if member.issym() or member.islnk():
                    link = Path(member.linkname)
                    resolved_link = (target.parent / link).resolve()
                    if link.is_absolute() or (resolved_link != destination.resolve()
                                               and destination.resolve() not in resolved_link.parents):
                        raise ValueError("Runtime archive contains an unsafe link")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    os.symlink(os.path.relpath(resolved_link, target.parent), target)
                elif member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    source = bundle.extractfile(member)
                    if source is not None:
                        with source, target.open("wb") as output:
                            shutil.copyfileobj(source, output)
                        target.chmod(member.mode & 0o777)
    elif zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.infolist():
                relative = Path(member.filename)
                if relative.is_absolute() or ".." in relative.parts:
                    raise ValueError("Runtime archive contains an unsafe path")
                parts = relative.parts[1:] if relative.parts and relative.parts[0] == strip_prefix else relative.parts
                if not parts:
                    continue
                target = _safe_target(destination, Path(*parts))
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with bundle.open(member) as source, target.open("wb") as output:
                        shutil.copyfileobj(source, output)
    else:
        raise ValueError("Unsupported runtime archive format")
    return destination


def _trim_runtime(runtime, platform_name):
    """Drop development headers and tools not needed to run Glacier."""
    for relative in ("include", "share/man", "share/doc", "lib/pkgconfig", "lib/python3.12/test",
                     "lib/python3.12/ensurepip", "Scripts", "include"):
        candidate = runtime / relative
        if candidate.exists():
            shutil.rmtree(candidate) if candidate.is_dir() and not candidate.is_symlink() else candidate.unlink()
    if platform_name != "x86_64-pc-windows-msvc":
        binaries = runtime / "bin"
        for name in ("2to3-3.12", "2to3", "idle3.12", "idle3", "pydoc3.12", "pydoc3",
                     "python3.12-config", "python3-config"):
            (binaries / name).unlink(missing_ok=True)
    else:
        for name in ("idle3.12.exe", "idle3.exe", "2to3.exe", "pydoc3.exe"):
            (runtime / name).unlink(missing_ok=True)


def _python_path(runtime, platform_name):
    if platform_name == "x86_64-pc-windows-msvc":
        return runtime / "python.exe"
    return runtime / "bin" / "python3.12"


def _site_packages(runtime, platform_name):
    if platform_name == "x86_64-pc-windows-msvc":
        return runtime / "Lib" / "site-packages"
    return runtime / "lib" / "python3.12" / "site-packages"


def install_requirements(runtime, platform_name, requirements=ROOT / "setup" / "requirements.txt"):
    python = _python_path(runtime, platform_name)
    site_packages = _site_packages(runtime, platform_name)
    site_packages.mkdir(parents=True, exist_ok=True)
    spec = ASSETS[platform_name]
    # Use the offline packer's shared cross-platform wheel resolver so both
    # installers accept the same pinned requirements and platform tags.
    offline_builder_path = ROOT / "setup" / "offline" / "build_pack.py"
    offline_spec = importlib.util.spec_from_file_location("glacier_offline_build_pack", offline_builder_path)
    offline_builder = importlib.util.module_from_spec(offline_spec)
    offline_spec.loader.exec_module(offline_builder)
    wheel_platform = spec["wheels"]
    with tempfile.TemporaryDirectory(prefix="glacier-runtime-wheels-") as wheel_dir:
        Path(wheel_dir).mkdir(parents=True, exist_ok=True)
        download = offline_builder.download_command(requirements, wheel_dir, wheel_platform, "3.12")
        subprocess.run(download, check=True)
        if platform_name == "x86_64-pc-windows-msvc":
            install = [sys.executable, "-m", "pip", "install", "--no-index", "--find-links", wheel_dir,
                       "--only-binary=:all:", "--platform", "win_amd64", "--python-version", "3.12",
                       "--implementation", "cp", "--abi", "cp312", "--target", str(site_packages),
                       "--requirement", str(requirements)]
        else:
            install = [str(python), "-m", "pip", "install", "--no-index", "--find-links", wheel_dir,
                       "--only-binary=:all:", "--no-warn-script-location", "--target", str(site_packages),
                       "--requirement", str(requirements)]
        subprocess.run(install, check=True)
    if platform_name != "x86_64-pc-windows-msvc":
        # Target installs avoid activation/venv metadata and remain relocatable.
        (site_packages / "_glacier_runtime.pth").write_text("", encoding="utf-8")


def build_runtime(platform_name, output=ROOT / "desktop" / "runtime", download=True):
    if platform_name not in ASSETS:
        raise ValueError("Unsupported platform: " + platform_name)
    spec = ASSETS[platform_name]
    output = Path(output) / platform_name
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="glacier-python-") as temporary:
        archive = Path(temporary) / spec["archive"]
        if download:
            url = BASE_URL + urllib.request.quote(spec["archive"])
            urllib.request.urlretrieve(url, archive)
        verify_sha256(archive, spec["sha256"])
        staging = Path(temporary) / "runtime"
        extract_runtime(archive, staging)
        _trim_runtime(staging, platform_name)
        install_requirements(staging, platform_name)
        if output.exists():
            shutil.rmtree(output)
        shutil.copytree(staging, output, symlinks=True)
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build Glacier's bundled Python runtime.")
    parser.add_argument("--platform", choices=ASSETS, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "desktop" / "runtime")
    args = parser.parse_args(argv)
    try:
        result = build_runtime(args.platform, args.output)
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        print("Could not build the Python runtime: " + str(exc), file=sys.stderr)
        return 1
    print("Runtime created at " + str(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
