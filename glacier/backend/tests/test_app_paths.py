from pathlib import Path

from app_paths import app_data_home, state_file


def test_app_data_root_uses_override_and_keeps_state_files_together(tmp_path, monkeypatch):
    home = tmp_path / "installed-data"
    monkeypatch.setenv("GLACIER_HOME", str(home))
    assert app_data_home() == home.resolve()
    assert state_file("hygiene.json") == home.resolve() / "hygiene.json"
    assert state_file("import_sources.json").parent == state_file("hygiene.json").parent


def test_app_data_root_defaults_to_local_data_folder(tmp_path, monkeypatch):
    monkeypatch.delenv("GLACIER_HOME", raising=False)
    monkeypatch.chdir(tmp_path)
    assert app_data_home() == (Path("data").resolve())
