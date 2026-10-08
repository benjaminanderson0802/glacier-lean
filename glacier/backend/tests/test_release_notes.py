def test_release_notes_returns_installed_version_markdown(server):
    from routes import releases
    releases._installed_version = lambda: "0.2.0"
    response = server.get("/api/releases/current")
    assert response.status_code == 200
    assert response.json() == {
        "version": "0.2.0",
        "markdown": "Release notes are added when the release is prepared.",
    }


def test_seen_version_is_saved_without_replacing_other_settings(server):
    assert server.get("/api/releases/installed/seen").json() == {"version": ""}
    assert server.put("/api/releases/installed/seen", json={"version": "0.2.0"}).json() == {"version": "0.2.0"}
    assert server.get("/api/releases/installed/seen").json() == {"version": "0.2.0"}
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
    assert notes.read_text(encoding="utf-8").strip() == "Release notes are added when the release is prepared."
