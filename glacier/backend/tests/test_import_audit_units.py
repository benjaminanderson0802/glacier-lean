"""Unit coverage for reporting actual import writes in audit events."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routes import imports


@pytest.mark.parametrize("multipart", [False, True])
def test_import_audit_counts_added_and_updated_notes(monkeypatch, multipart):
    events = []
    monkeypatch.setattr(imports.import_service, "import_export", lambda *args, **kwargs: {
        "added": 2, "updated": 1, "unchanged": 7,
    })
    monkeypatch.setattr(imports.audit_log, "record", lambda action, **kwargs: events.append((action, kwargs)))
    app = FastAPI()
    app.include_router(imports.router)
    with TestClient(app) as client:
        if multipart:
            response = client.post("/api/imports", data={"source": "chatgpt"},
                                   files={"file": ("export.json", b"[]", "application/json")})
        else:
            response = client.post("/api/imports", json={"source": "chatgpt", "path": "/export.json"})
    assert response.status_code == 200
    assert events == [("memory.imported", {"what": {"source": "chatgpt", "written": 3}})]


def test_refresh_audit_totals_writes_from_both_sources(monkeypatch):
    events = []
    monkeypatch.setattr(imports.import_service, "refresh", lambda: {
        "chatgpt": {"added": 1, "updated": 2, "unchanged": 4},
        "claude": {"added": 3, "updated": 0, "unchanged": 5},
    })
    monkeypatch.setattr(imports.audit_log, "record", lambda action, **kwargs: events.append((action, kwargs)))
    result = imports.refresh_imports()
    assert len(result) == 2
    assert events == [("memory.imports_refreshed", {"what": {"written": 6}})]
