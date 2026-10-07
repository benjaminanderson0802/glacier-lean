import os

import httpx


def test_upload_text_is_stored_and_searchable(server):
    response = httpx.post(server.url + "/api/files", files={"file": ("meeting.md", b"# Meeting\n\nQuasar agenda details.", "text/markdown")}, data={"project": "Research"})
    assert response.status_code == 200, response.text
    item = response.json()
    assert item["name"] == "meeting.md"
    assert item["project"] == "Research"
    assert item["note"] == "files/Research/meeting.md.md"
    assert os.path.isfile(os.path.join(server.home, "files", "Research", "meeting.md"))
    found = httpx.get(server.url + "/api/memory/search", params={"q": "Quasar"}).json()
    assert any(row["path"] == item["note"] for row in found)


def test_upload_html_is_converted_to_searchable_note(server):
    document = b"<!doctype html><html><body><h1>Bluejay brief</h1><p>Document phrase searchable here.</p></body></html>"
    response = httpx.post(server.url + "/api/files", files={"file": ("brief.html", document, "text/html")})
    assert response.status_code == 200, response.text
    result = httpx.get(server.url + "/api/memory/search", params={"q": "Bluejay"}).json()
    assert any(row["path"] == "files/Inbox/brief.html.md" for row in result)


def test_upload_rejects_path_traversal_filename(server):
    response = httpx.post(server.url + "/api/files", files={"file": ("../outside.txt", b"bad", "text/plain")})
    assert response.status_code == 400
    assert "file name" in response.text.lower()


def test_upload_rejects_executable(server):
    response = httpx.post(server.url + "/api/files", files={"file": ("setup.exe", b"not really executable", "application/octet-stream")})
    assert response.status_code == 400
    assert "not allowed" in response.text.lower()


def test_upload_rejects_file_over_configured_limit(monkeypatch, make_server):
    monkeypatch.setenv("GLACIER_MAX_UPLOAD_MB", "0.00001")
    server = make_server().start()
    response = httpx.post(server.url + "/api/files", files={"file": ("large.txt", b"This is too large", "text/plain")})
    assert response.status_code == 413
    assert "too large" in response.text.lower()


def test_duplicate_upload_returns_existing_entry(server):
    payload = {"file": ("same.txt", b"A duplicate document", "text/plain")}
    first = httpx.post(server.url + "/api/files", files=payload).json()
    second = httpx.post(server.url + "/api/files", files=payload).json()
    assert second["duplicate"] is True
    assert second["sha256"] == first["sha256"]
    assert len(httpx.get(server.url + "/api/files").json()) == 1


def test_projects_can_be_created_and_listed(server):
    response = httpx.post(server.url + "/api/projects", json={"name": "Field Notes"})
    assert response.status_code == 200, response.text
    projects = httpx.get(server.url + "/api/projects").json()
    assert {p["name"] for p in projects} >= {"Inbox", "Field Notes"}
    assert next(p for p in projects if p["name"] == "Inbox")["count"] == 0


def test_project_name_is_plain_and_windows_safe(server):
    for name in ("../escape", "A/B", "CON", "trailing."):
        response = httpx.post(server.url + "/api/projects", json={"name": name})
        assert response.status_code == 400
