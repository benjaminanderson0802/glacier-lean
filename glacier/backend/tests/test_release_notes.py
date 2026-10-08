def test_release_notes_returns_installed_version_markdown(server):
    """The running server reports the bundled app version and that version's notes file."""
    from pathlib import Path
    from desktop_version import _version
    version = _version()
    notes = Path(__file__).resolve().parents[3] / "docs" / "releases" / f"v{version}.md"
    assert server.get("/api/releases/current") == {"version": version, "markdown": notes.read_text(encoding="utf-8")}


def test_seen_version_is_saved_without_replacing_other_settings(server):
    assert server.get("/api/releases/installed/seen") == {"version": ""}
    assert server.put("/api/releases/installed/seen", {"version": "0.2.0"}) == {"version": "0.2.0"}
    assert server.get("/api/releases/installed/seen") == {"version": "0.2.0"}
    import json
    from pathlib import Path
    settings = json.loads((Path(server.home) / "settings.json").read_text(encoding="utf-8"))
    assert settings["last_seen_app_version"] == "0.2.0"


def test_install_layout_includes_release_notes(tmp_path):
    from test_install_layout import _install

    app_dir = tmp_path / "app"
    _install(app_dir)
    notes = app_dir / "docs" / "releases" / "v0.2.0.md"
    assert notes.is_file()
    assert notes.read_text(encoding="utf-8").strip()
