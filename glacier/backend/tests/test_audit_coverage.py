"""Audit coverage contracts: successful API effects emit one safe, timestamped event."""
import json
import os

import pytest
from fastapi.testclient import TestClient

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _route_key(route):
    methods = sorted((getattr(route, "methods", None) or set()) - {"HEAD", "OPTIONS"})
    return {f"{method} {route.path}" for method in methods}


@pytest.fixture
def audit_modules(isolated_git_home, tmp_path, monkeypatch):
    # Importing app initializes the vault and commits its initial state. Keep that
    # effect inside a test fixture, after GLACIER_HOME and Git identity are set.
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path / "backend-home"))
    import sys

    if BACKEND not in sys.path:
        sys.path.insert(0, BACKEND)
    import audit_inventory
    import audit_log
    import app
    import vault
    return audit_inventory, audit_log, app, vault


@pytest.fixture
def isolated_git_home(tmp_path, monkeypatch):
    home = tmp_path / "git-home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(home / "no-global-config"))
    # Vault initialization makes a commit, so give that repository a local identity.
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Audit Test")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "audit-test@localhost")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Audit Test")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "audit-test@localhost")
    return home


def test_side_effect_route_inventory_has_audit_declaration(audit_modules):
    audit_inventory, _, app, _ = audit_modules
    # Include every mutating API route. Read-only routes are not effects; newly added
    # mutating routes must be consciously classified in AUDITED_ROUTES.
    actual = set()
    for route in app.app.routes:
        if not getattr(route, "path", "").startswith("/api/"):
            continue
        for key in _route_key(route):
            if key.split(" ", 1)[0] in {"POST", "PUT", "PATCH", "DELETE"}:
                actual.add(key)
    missing = actual - set(audit_inventory.AUDITED_ROUTES)
    assert not missing, f"mutating routes need an audit classification: {sorted(missing)}"


def test_effect_node_inventory_has_audit_declaration(audit_modules):
    audit_inventory, _, _, _ = audit_modules
    catalog_path = os.path.abspath(os.path.join(BACKEND, "..", "contract", "node_types.json"))
    catalog = json.loads(open(catalog_path, encoding="utf-8").read())
    known = {item["type"] for item in catalog["types"]}
    # Existing ordinary control nodes do not cause side effects. These types do.
    assert audit_inventory.SIDE_EFFECT_NODE_TYPES <= known | set(audit_inventory.AUDITED_NODES)
    assert set(audit_inventory.AUDITED_NODES) == audit_inventory.SIDE_EFFECT_NODE_TYPES


@pytest.fixture
def audit_client(tmp_path, monkeypatch, isolated_git_home, audit_modules):
    _, audit_log, _, vault = audit_modules
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    vault.init(str(tmp_path / "vault"))
    from routes import secrets as secret_routes
    from routes import files as file_routes
    from routes import hygiene as hygiene_routes
    local_app = __import__("fastapi").FastAPI()
    local_app.include_router(secret_routes.router)
    local_app.include_router(file_routes.router)
    local_app.include_router(hygiene_routes.router)
    return TestClient(local_app), tmp_path, audit_log


@pytest.mark.parametrize("method,path,body,event", [
    ("put", "/api/secrets/EXAMPLE_TOKEN", {"value": "never-log-this-value"}, "secret.set"),
    ("delete", "/api/secrets/EXAMPLE_TOKEN", None, "secret.deleted"),
    ("post", "/api/projects", {"name": "Audit project"}, "project.created"),
])
def test_api_effect_records_exactly_one_audit_event(audit_client, monkeypatch, method, path, body, event):
    client, home, audit_log = audit_client
    # Secret store is stubbed at its effect boundary: test behavior, not OS keychain availability.
    if event.startswith("secret."):
        import secrets_store
        monkeypatch.setattr(secrets_store, "set", lambda *_: None)
        monkeypatch.setattr(secrets_store, "delete", lambda *_: None)
    response = getattr(client, method)(path, json=body) if body is not None else getattr(client, method)(path)
    assert response.status_code == 200
    rows = audit_log.events(home=str(home))
    matched = [row for row in rows if row["event_type"] == event]
    assert len(matched) == 1
    assert matched[0]["who"] == "owner" and matched[0]["when"]
    if event.startswith("secret."):
        assert matched[0]["what"] == {"name": "EXAMPLE_TOKEN"}
        assert "never-log-this-value" not in json.dumps(rows)


def test_run_api_start_has_exactly_one_audit_event(server, isolated_git_home, audit_modules):
    _, audit_log, _, _ = audit_modules
    from conftest import env
    graph = env("audit-start", [("cmd", "command", {"cmd": "true"})], [])
    server.put("/api/environments/audit-start", graph)
    start = server.post("/api/environments/audit-start/run")
    server.wait_run(start["run_id"])
    rows = audit_log.events("run.started", home=server.home)
    matches = [row for row in rows if row["what"].get("run_id") == start["run_id"]]
    assert len(matches) == 1
    assert matches[0]["what"]["source"] == "runtime"
