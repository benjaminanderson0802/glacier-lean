import os
from concurrent.futures import ThreadPoolExecutor

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


def test_upload_rejects_executable_magic_bytes_named_as_text(server):
    response = httpx.post(server.url + "/api/files", files={"file": ("notes.txt", b"MZ" + b"\x00" * 64, "text/plain")})
    assert response.status_code == 400
    assert "not allowed" in response.text.lower()


def test_upload_rejects_file_over_configured_limit(monkeypatch, make_server):
    monkeypatch.setenv("GLACIER_MAX_UPLOAD_MB", "0.00001")
    server = make_server().start()
    response = httpx.post(server.url + "/api/files", files={"file": ("large.txt", b"This is too large", "text/plain")})
    assert response.status_code == 413
    assert "too large" in response.text.lower()
    assert "0.00001 MB" in response.text


def test_request_body_over_limit_is_rejected_while_streaming(monkeypatch, make_server):
    monkeypatch.setenv("GLACIER_MAX_UPLOAD_MB", "0.00001")
    server = make_server().start()
    response = httpx.post(
        server.url + "/api/files",
        files={"file": ("large.txt", b"x" * (128 * 1024), "text/plain")},
    )
    assert response.status_code == 413
    assert "too large" in response.text.lower()
    assert httpx.get(server.url + "/api/files").json() == []


def test_bounded_body_reader_stops_before_consuming_remaining_chunks(monkeypatch):
    import asyncio
    import files_store
    import routes.files as files_routes

    monkeypatch.setattr(files_store, "max_upload_bytes", lambda: 10)

    class StreamingRequest:
        headers = {}
        consumed = 0

        async def stream(self):
            self.consumed += 1
            yield b"x" * (10 + 64 * 1024 + 1)
            self.consumed += 1
            yield b"remaining"

    request = StreamingRequest()
    try:
        asyncio.run(files_routes._read_bounded_body(request))
    except files_routes.HTTPException as exc:
        assert exc.status_code == 413
    else:
        raise AssertionError("oversized request body was accepted")
    assert request.consumed == 1


def test_concurrent_uploads_both_appear_in_project_index(server):
    def upload(filename, content):
        return httpx.post(server.url + "/api/files", files={"file": (filename, content, "text/plain")}, timeout=30)

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda item: upload(*item), [
            ("first.txt", b"concurrent first contents"),
            ("second.txt", b"concurrent second contents"),
        ]))
    assert [response.status_code for response in responses] == [200, 200]
    assert {row["name"] for row in httpx.get(server.url + "/api/files").json()} == {"first.txt", "second.txt"}


def test_conversion_sets_memory_limit_inside_child_without_preexec(monkeypatch, tmp_path):
    import subprocess
    import files_store

    captured = {}

    def fake_run(args, **kwargs):
        captured.update(kwargs)
        captured["script"] = args[2]
        return subprocess.CompletedProcess(args, 0, stdout=b"Readable", stderr=b"")

    monkeypatch.setattr(files_store.subprocess, "run", fake_run)
    files_store._convert_in_child(tmp_path / "example.txt")
    assert "preexec_fn" not in captured
    assert "resource.setrlimit(resource.RLIMIT_AS" in captured["script"]


def test_index_is_persisted_and_same_name_upload_uses_new_name(server):
    first = httpx.post(server.url + "/api/files", files={"file": ("same.txt", b"first body", "text/plain")}).json()
    second = httpx.post(server.url + "/api/files", files={"file": ("same.txt", b"second body", "text/plain")}).json()
    assert first["name"] == "same.txt"
    assert second["name"] == "same (2).txt"
    index_path = os.path.join(server.home, "files", "Inbox", ".index.json")
    assert os.path.isfile(index_path)
    assert len(httpx.get(server.url + "/api/files").json()) == 2


def test_upload_docx_is_converted_and_searchable(server):
    import io
    from zipfile import ZIP_DEFLATED, ZipFile
    content = io.BytesIO()
    with ZipFile(content, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'></Types>")
        archive.writestr("word/document.xml", "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'><w:body><w:p><w:r><w:t>Zirconium report searchable phrase</w:t></w:r></w:p></w:body></w:document>")
    response = httpx.post(server.url + "/api/files", files={"file": ("report.docx", content.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
    assert response.status_code == 200, response.text
    result = response.json()
    assert os.path.isfile(os.path.join(server.home, result["path"]))
    if result.get("note"):
        found = httpx.get(server.url + "/api/memory/search", params={"q": "Zirconium"}).json()
        assert any(row["path"] == result["note"] for row in found)
    else:
        # This environment may omit MarkItDown's optional docx extra.
        assert result.get("message") == "File saved, but its text couldn't be read."


def test_upload_reports_vault_write_failure(tmp_path, monkeypatch):
    import files_store
    import vault
    import io
    def fail(*args, **kwargs):
        raise OSError("vault unavailable")
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    monkeypatch.setattr(vault, "VAULT", str(tmp_path / "vault"))
    monkeypatch.setattr(files_store, "_convert_in_child", lambda path: "Readable words " + path.name)
    monkeypatch.setattr(vault, "write_note", fail)
    result = files_store.save_upload("write-failure.txt", None, io.BytesIO(b"Unique vault failure words"))
    assert "saved" in result.get("message", "").lower()
    assert "note could not be saved" in result.get("message", "").lower()


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
