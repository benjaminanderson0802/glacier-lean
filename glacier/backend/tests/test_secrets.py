import json

import keyring
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import secrets_store
from routes import secrets as secrets_routes


class MemoryKeyring(keyring.backend.KeyringBackend):
    """Small in-memory backend for isolated secret-store tests."""

    priority = 1

    def __init__(self):
        self.values = {}

    def get_password(self, service, username):
        return self.values.get((service, username))

    def set_password(self, service, username, password):
        self.values[(service, username)] = password

    def delete_password(self, service, username):
        del self.values[(service, username)]


@pytest.fixture
def secret_client(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    keyring.set_keyring(MemoryKeyring())
    app = FastAPI()
    app.include_router(secrets_routes.router)
    return TestClient(app), tmp_path


def test_api_stores_values_only_in_keyring_and_redacts_them(secret_client):
    client, home = secret_client
    secret_value = "super-private-token-123"

    response = client.put("/api/secrets/weather-api", json={"value": secret_value})

    assert response.status_code == 200
    assert response.json() == {"saved": True}
    assert secret_value not in response.text
    assert client.get("/api/secrets").json() == ["weather-api"]
    names_file = home / "secret_names.json"
    assert json.loads(names_file.read_text()) == ["weather-api"]
    assert secret_value not in names_file.read_text()
    assert secrets_store.redact(f"sent {secret_value}") == "sent [secret weather-api]"


def test_resolve_replaces_known_names_and_rejects_unknown_names(secret_client):
    client, _ = secret_client
    client.put("/api/secrets/login", json={"value": "pw-456"})

    assert secrets_store.resolve("Authorization: {secret:login}") == "Authorization: pw-456"
    with pytest.raises(ValueError, match="Unknown secret: missing"):
        secrets_store.resolve("{secret:missing}")


def test_delete_removes_name_and_secret(secret_client):
    client, home = secret_client
    client.put("/api/secrets/temporary", json={"value": "remove-me"})

    response = client.delete("/api/secrets/temporary")

    assert response.status_code == 200
    assert client.get("/api/secrets").json() == []
    assert json.loads((home / "secret_names.json").read_text()) == []
    assert secrets_store.redact("remove-me") == "remove-me"


def test_redact_replaces_longer_overlapping_value_first(secret_client):
    client, _ = secret_client
    client.put("/api/secrets/short", json={"value": "abc123"})
    client.put("/api/secrets/long", json={"value": "abc123-long-suffix"})

    assert secrets_store.redact("x abc123-long-suffix y") == "x [secret long] y"


def test_redact_skips_empty_and_short_values(secret_client):
    client, _ = secret_client
    client.put("/api/secrets/empty", json={"value": ""})
    client.put("/api/secrets/tiny", json={"value": "abc"})

    assert secrets_store.redact("normal output abc") == "normal output abc"
