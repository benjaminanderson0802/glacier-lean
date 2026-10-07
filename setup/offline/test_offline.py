import hashlib
import io
import json
import zipfile
import sys
import tarfile
import argparse
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_pack
import install_pack


def make_pack(tmp_path):
    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "wheels").mkdir()
    (pack / "wheels" / "sample-1.0-py3-none-any.whl").write_bytes(b"wheel-data")
    (pack / "README.txt").write_text("Offline pack\n", encoding="utf-8")
    build_pack.write_manifest(pack)
    return pack


def test_manifest_verification_detects_tampered_file(tmp_path):
    pack = make_pack(tmp_path)
    assert install_pack.verify_manifest(pack) == []
    (pack / "wheels" / "sample-1.0-py3-none-any.whl").write_bytes(b"changed")
    problems = install_pack.verify_manifest(pack)
    assert any("sample-1.0-py3-none-any.whl" in problem for problem in problems)


def test_install_refuses_pack_mismatch_before_creating_environment(tmp_path):
    pack = make_pack(tmp_path)
    (pack / "wheels" / "sample-1.0-py3-none-any.whl").write_bytes(b"tampered")
    destination = tmp_path / "installed"
    with patch.object(install_pack, "create_environment") as create_environment:
        result = install_pack.install(pack, destination)
    assert result is False
    create_environment.assert_not_called()
    assert not destination.exists()


def test_build_pack_creates_wheels_docs_manifest_and_readme(tmp_path):
    repo = tmp_path / "repo"
    (repo / "setup").mkdir(parents=True)
    (repo / "docs" / "guide").mkdir(parents=True)
    (repo / "setup" / "requirements.txt").write_text("sample==1.0\n", encoding="utf-8")
    (repo / "docs" / "guide" / "README.md").write_text("# Hello\n\nOffline guide.\n", encoding="utf-8")
    output = tmp_path / "output"
    fake_wheel = tmp_path / "sample-1.0-py3-none-any.whl"
    with zipfile.ZipFile(fake_wheel, "w") as archive:
        archive.writestr("sample-1.0.dist-info/METADATA", "Name: sample\nVersion: 1.0\n")

    def fake_download(requirements, destination, platform_name, python_version):
        assert requirements.read_text(encoding="utf-8").strip() == "sample==1.0"
        assert platform_name == ["manylinux_2_28_x86_64", "manylinux_2_27_x86_64",
                                 "manylinux_2_17_x86_64", "manylinux2014_x86_64"]
        assert python_version == "3.12"
        destination.mkdir(parents=True)
        (destination / fake_wheel.name).write_bytes(fake_wheel.read_bytes())

    def fake_archive(repo_root, destination):
        destination.mkdir(parents=True)
        (destination / "glacier-source.tar").write_bytes(b"mock source archive")

    with patch.object(build_pack, "download_wheels", side_effect=fake_download), \
         patch.object(build_pack, "_source_archive", side_effect=fake_archive):
        result = build_pack.build_pack(
            repo_root=repo, output=output, platform_name=["manylinux_2_28_x86_64",
                "manylinux_2_27_x86_64", "manylinux_2_17_x86_64", "manylinux2014_x86_64"],
            python_version="3.12", ollama_model=None, include_model=False,
        )
    assert result == output
    assert (output / "wheels" / fake_wheel.name).is_file()
    assert (output / "docs" / "index.html").is_file() or (output / "docs" / "README.md").is_file()
    assert (output / "README.txt").is_file()
    manifest = json.loads((output / "MANIFEST.json").read_text(encoding="utf-8"))
    listed = {item["path"]: item["sha256"] for item in manifest["files"]}
    assert "README.txt" in listed
    for relative, digest in listed.items():
        assert hashlib.sha256((output / relative).read_bytes()).hexdigest() == digest
    assert "MANIFEST.json" not in listed


def test_linux_build_uses_multiple_platform_tags():
    command = build_pack.download_command(Path("requirements.txt"), Path("wheels"),
                                          build_pack.LINUX_PLATFORMS, "3.12")
    platform_args = [command[index + 1] for index, value in enumerate(command[:-1])
                     if value == "--platform"]
    assert platform_args == list(build_pack.LINUX_PLATFORMS)


def test_cli_accepts_repeated_platform_tags(tmp_path):
    repo = tmp_path / "repo"
    (repo / "setup").mkdir(parents=True)
    (repo / "docs" / "guide").mkdir(parents=True)
    (repo / "setup" / "requirements.txt").write_text("sample==1.0\n", encoding="utf-8")
    (repo / "docs" / "guide" / "README.md").write_text("# Hello\n", encoding="utf-8")
    with patch.object(build_pack, "build_pack") as build:
        with patch.object(sys, "argv", ["build_pack.py", "--platform", "manylinux_2_28_x86_64",
                                         "--platform", "manylinux_2_27_x86_64"]):
            assert build_pack.main() == 0
    assert build.call_args.kwargs["platform_name"] == ["manylinux_2_28_x86_64",
                                                        "manylinux_2_27_x86_64"]


def test_zip_output_contains_complete_pack(tmp_path):
    pack = make_pack(tmp_path)
    archive = tmp_path / "pack.zip"
    build_pack.zip_pack(pack, archive)
    with zipfile.ZipFile(archive) as zipped:
        assert "pack/MANIFEST.json" in zipped.namelist()
        assert "pack/README.txt" in zipped.namelist()


def test_manifest_rejects_windows_paths_and_paths_resolving_outside(tmp_path):
    pack = make_pack(tmp_path)
    manifest_path = pack / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"].append({"path": "..\\outside.txt", "sha256": "0" * 64})
    manifest["files"].append({"path": "drive:C.txt", "sha256": "0" * 64})
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    problems = install_pack.verify_manifest(pack)
    assert sum("unsafe" in problem.lower() for problem in problems) >= 2


def test_install_checks_metadata_and_manifest_digest_before_environment(tmp_path):
    pack = make_pack(tmp_path)
    manifest_path = pack / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["metadata"] = {"platform": "win_amd64", "python_version": "3.12"}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    destination = tmp_path / "installed"
    with patch.object(install_pack.platform, "system", return_value="Linux"), \
         patch.object(install_pack, "create_environment") as create_environment:
        assert not install_pack.install(pack, destination)
    create_environment.assert_not_called()


def test_install_uses_manifest_wheel_paths_and_copies_source(tmp_path):
    pack = make_pack(tmp_path)
    (pack / "source").mkdir()
    (pack / "source" / "app.py").write_text("print('source')\n", encoding="utf-8")
    build_pack.write_manifest(pack, {"platform": "manylinux2014_x86_64", "python_version": "3.12"})
    destination = tmp_path / "installed"
    captured = {}
    def fake_run(command, **kwargs):
        captured["command"] = command
        return None
    with patch.object(install_pack.platform, "system", return_value="Linux"), \
         patch.object(install_pack.platform, "machine", return_value="x86_64"), \
         patch.object(install_pack.sys, "version_info", (3, 12, 2)), \
         patch.object(install_pack, "create_environment"), \
         patch.object(install_pack, "_install_source", side_effect=lambda pack, dest: (Path(dest).mkdir(parents=True, exist_ok=True), (Path(dest) / "source").mkdir())[0] is None), \
         patch.object(install_pack.subprocess, "run", side_effect=fake_run), \
         patch.object(install_pack, "_check_tools"):
        assert install_pack.install(pack, destination)
    command = captured["command"]
    assert str(pack / "wheels" / "sample-1.0-py3-none-any.whl") in command
    assert "*.whl" not in command
    assert (destination / "source").is_dir()


def test_mocked_build_pack_can_be_installed_and_copies_git_archive(tmp_path):
    repo = tmp_path / "repo"
    (repo / "setup").mkdir(parents=True)
    (repo / "docs" / "guide").mkdir(parents=True)
    (repo / "setup" / "requirements.txt").write_text("sample==1.0\n", encoding="utf-8")
    (repo / "docs" / "guide" / "README.md").write_text("# Hello\n", encoding="utf-8")
    wheel = tmp_path / "sample-1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("sample-1.0.dist-info/METADATA", "Name: sample\nVersion: 1.0\n")
    def fake_download(requirements, destination, platform_name, python_version):
        destination.mkdir(parents=True)
        (destination / wheel.name).write_bytes(wheel.read_bytes())
    def fake_archive(repo_root, destination):
        destination.mkdir(parents=True)
        source_tar = destination / "glacier-source.tar"
        with tarfile.open(source_tar, "w") as archive:
            payload = b"print('clean source')\n"
            info = tarfile.TarInfo("glacier/app.py")
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    pack = tmp_path / "built-pack"
    with patch.object(build_pack, "download_wheels", side_effect=fake_download), \
         patch.object(build_pack, "_source_archive", side_effect=fake_archive):
        build_pack.build_pack(repo_root=repo, output=pack,
                              platform_name="manylinux2014_x86_64", python_version="3.12")
    destination = tmp_path / "installed"
    with patch.object(install_pack.platform, "system", return_value="Linux"), \
         patch.object(install_pack.platform, "machine", return_value="x86_64"), \
         patch.object(install_pack.sys, "version_info", (3, 12, 0)), \
         patch.object(install_pack, "create_environment", side_effect=lambda dest: Path(dest).mkdir()), \
         patch.object(install_pack.subprocess, "run", return_value=None), \
         patch.object(install_pack, "_check_tools"):
        assert install_pack.install(pack, destination)
    assert (destination / "source" / "glacier" / "app.py").read_text(encoding="utf-8") == "print('clean source')\n"
