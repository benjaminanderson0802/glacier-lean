from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from ventures.blocks.mail import engine


class FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None):
        self.status_code = status_code
        self.headers = headers or {}
        self._payload = payload or {}

    def json(self):
        return self._payload


class FakeTransport:
    def __init__(self, response=None, error=None):
        self.calls = []
        self.response = response or FakeResponse(payload={"ok": True})
        self.error = error

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if self.error:
            raise self.error
        return self.response


class FakeSecrets:
    def __init__(self, value):
        self.value = value
        self.lookups = []

    def resolve(self, reference):
        self.lookups.append(reference)
        if reference != "{secret:LOB_API_KEY}" or self.value is None:
            raise ValueError("missing synthetic secret")
        return self.value


def _getter(value):
    return lambda name: value if name == "LOB_API_KEY" else None


def test_glacier_secret_store_is_used_and_environment_key_is_ignored(monkeypatch):
    secret = "test_mail_secrets_synthetic"
    store = FakeSecrets(secret)
    monkeypatch.setattr(engine, "_secrets_store", lambda: store, raising=False)
    monkeypatch.setenv("LOB_API_KEY", "environment_must_not_be_used")
    transport = FakeTransport()

    engine._lob_request("addresses/validate", transport=transport)

    assert store.lookups == ["{secret:LOB_API_KEY}"]
    assert transport.calls[0][1].startswith("https://api.lob.com/v1/")
    authorization = transport.calls[0][2]["auth"]
    assert authorization == (secret, "")


def test_live_key_is_rejected_before_transport():
    transport = FakeTransport()

    with pytest.raises(ValueError, match="test key"):
        engine._lob_request(
            "addresses/validate", secret_getter=_getter("live_synthetic"), transport=transport
        )

    assert transport.calls == []


def test_redirect_is_not_followed_and_transport_error_does_not_echo_key():
    secret = "test_mail_secrets_synthetic"
    redirect = FakeTransport(FakeResponse(302, headers={"Location": "https://evil.invalid/"}))

    with pytest.raises(RuntimeError, match="redirect"):
        engine._lob_request("addresses/validate", secret_getter=_getter(secret), transport=redirect)
    assert len(redirect.calls) == 1

    failed = FakeTransport(error=RuntimeError(f"upstream exposed {secret}"))
    with pytest.raises(RuntimeError) as caught:
        engine._lob_request("addresses/validate", secret_getter=_getter(secret), transport=failed)
    assert secret not in str(caught.value)
    assert caught.value.__cause__ is None


def test_no_secret_postcard_stays_render_only_without_http(tmp_path):
    transport = FakeTransport()
    with patch.dict("os.environ", {"LOB_API_KEY": "environment_synthetic"}):
        result = engine.postcard(
            "<main>Front Synthetic Sender</main>", "<main>Back</main>",
            {"address": "100 Main St"}, {"name": "Synthetic Sender"},
            output_dir=tmp_path, secret_getter=_getter(None), transport=transport,
        )

    assert result["status"] == "render_only"
    assert Path(result["proof_pdf"]).is_file()
    assert transport.calls == []


def test_configured_unapproved_base_is_rejected_before_transport(monkeypatch):
    transport = FakeTransport()
    monkeypatch.setenv("LOB_API_BASE_URL", "https://evil.invalid/v1")

    with pytest.raises(ValueError, match="approved"):
        engine._lob_request(
            "addresses/validate", secret_getter=_getter("test_mail_secrets_synthetic"),
            transport=transport,
        )

    assert transport.calls == []
