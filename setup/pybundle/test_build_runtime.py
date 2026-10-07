"""Offline acceptance checks for portable runtime archive handling."""
import importlib.util
from pathlib import Path
import tarfile
import zipfile


SCRIPT = Path(__file__).with_name("build_runtime.py")
SPEC = importlib.util.spec_from_file_location("build_runtime", SCRIPT)
build_runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build_runtime)


def test_hash_mismatch_is_refused(tmp_path):
    archive = tmp_path / "runtime.tar.gz"
    archive.write_bytes(b"untrusted runtime")

    try:
        build_runtime.verify_sha256(archive, "0" * 64)
    except ValueError as error:
        assert "SHA-256" in str(error)
    else:
        raise AssertionError("A runtime with a different SHA-256 was accepted")


def test_tiny_tar_archive_extracts_to_runtime_layout(tmp_path):
    archive = tmp_path / "runtime.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        item = tmp_path / "python"
        item.write_bytes(b"fake python")
        bundle.add(item, arcname="python/bin/python3.12")
        package = tmp_path / "fastapi.py"
        package.write_text("# fake package\n", encoding="utf-8")
        bundle.add(package, arcname="python/lib/python3.12/site-packages/fastapi.py")

    runtime = build_runtime.extract_runtime(archive, tmp_path / "runtime", "python")

    assert runtime == tmp_path / "runtime"
    assert (runtime / "bin/python3.12").read_bytes() == b"fake python"
    assert (runtime / "lib/python3.12/site-packages/fastapi.py").is_file()


def test_windows_zip_archive_extracts_to_runtime_layout(tmp_path):
    archive = tmp_path / "runtime.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("python/python.exe", b"fake python")
        bundle.writestr("python/Lib/site-packages/fastapi.py", "# fake package\n")

    runtime = build_runtime.extract_runtime(archive, tmp_path / "runtime", "python")

    assert (runtime / "python.exe").read_bytes() == b"fake python"
    assert (runtime / "Lib/site-packages/fastapi.py").is_file()


def test_windows_wheel_download_uses_binary_win_amd64_target(tmp_path, monkeypatch):
    commands = []

    def fake_run(command, check):
        commands.append(command)

    monkeypatch.setattr(build_runtime.subprocess, "run", fake_run)
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("fastapi==0.1\n", encoding="utf-8")
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "python.exe").write_bytes(b"fake python")

    build_runtime.install_requirements(runtime, "x86_64-pc-windows-msvc", requirements)

    download = commands[0]
    assert "download" in download
    assert "--platform" in download and download[download.index("--platform") + 1] == "win_amd64"
    assert "--only-binary=:all:" in download
    assert "--target" in commands[1]
    assert commands[1][commands[1].index("--target") + 1] == str(runtime / "Lib/site-packages")


def test_linux_wheel_download_accepts_offline_pack_compatible_tags(tmp_path, monkeypatch):
    commands = []

    def fake_run(command, check):
        commands.append(command)

    monkeypatch.setattr(build_runtime.subprocess, "run", fake_run)
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("sqlite-vec==0.1.9\n", encoding="utf-8")
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "bin").mkdir()
    (runtime / "bin/python3.12").write_bytes(b"fake python")

    build_runtime.install_requirements(runtime, "x86_64-unknown-linux-gnu", requirements)

    platforms = [command[index + 1] for command in commands for index, item in enumerate(command)
                 if item == "--platform"]
    assert platforms == ["manylinux_2_28_x86_64", "manylinux_2_27_x86_64",
                         "manylinux_2_17_x86_64", "manylinux2014_x86_64"]
    assert "--no-index" in commands[1]
    assert "--find-links" in commands[1]


def test_trim_removes_aliases_for_removed_development_tools(tmp_path):
    runtime = tmp_path / "runtime"
    binaries = runtime / "bin"
    binaries.mkdir(parents=True)
    (binaries / "python3.12-config").write_text("dev tool", encoding="utf-8")
    (binaries / "python3-config").symlink_to("python3.12-config")
    (binaries / "2to3-3.12").write_text("dev tool", encoding="utf-8")
    (binaries / "2to3").symlink_to("2to3-3.12")

    build_runtime._trim_runtime(runtime, "x86_64-unknown-linux-gnu")

    assert not (binaries / "python3-config").exists()
    assert not (binaries / "python3-config").is_symlink()
    assert not (binaries / "2to3").exists()
    assert not (binaries / "2to3").is_symlink()
