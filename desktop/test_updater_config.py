import json
from pathlib import Path


def test_tauri_updater_uses_public_repo_and_has_verification_key():
    config = json.loads(Path(__file__).parent.joinpath("src-tauri/tauri.conf.json").read_text())
    updater = config["plugins"]["updater"]
    assert updater["endpoints"] == [
        "https://github.com/benjaminanderson0802/glacier-lean/releases/latest/download/latest.json"
    ]
    assert isinstance(updater["pubkey"], str) and updater["pubkey"].strip()


def test_signing_artifacts_are_enabled_only_for_the_secret_gated_release_build():
    root = Path(__file__).parent.joinpath("src-tauri")
    release = json.loads(root.joinpath("tauri.release.windows.conf.json").read_text())
    assert release["bundle"]["createUpdaterArtifacts"] is True
    for filename in ("tauri.windows.conf.json", "tauri.linux.conf.json", "tauri.macos.conf.json"):
        config = json.loads(root.joinpath(filename).read_text())
        assert config["bundle"]["createUpdaterArtifacts"] is False
