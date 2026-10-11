from __future__ import annotations

import json
import sys
from pathlib import Path

VENTURE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(VENTURE_DIR))

from scripts.authorize_channels import SCOPES, authorize_all
from scripts.channels import CHANNEL_HANDLES


class CredentialsFixture:
    def __init__(self, handle):
        self.handle = handle

    def to_json(self):
        return json.dumps({"token": "fixture-secret-token", "handle": self.handle})


def test_oauth_loop_authorizes_each_channel_and_never_prints_token(tmp_path):
    (tmp_path / "tokens").mkdir()
    (tmp_path / "tokens" / "client_secret.json").write_text("{}", encoding="utf-8")
    selected = []
    output = []

    class Flow:
        def __init__(self, handle, scopes):
            assert scopes == SCOPES
            self.handle = handle

        def run_local_server(self, *, port, open_browser):
            assert port == 0
            assert open_browser is True
            selected.append(self.handle)
            return CredentialsFixture(self.handle)

    class Service:
        def __init__(self, handle):
            self.handle = handle

        def channels(self):
            return self

        def list(self, **kwargs):
            assert kwargs["mine"] is True
            assert kwargs["part"] == "id,snippet"
            return self

        def execute(self):
            return {"items": [{"id": "channel-id", "snippet": {
                "customUrl": self.handle, "title": self.handle,
            }}]}

    def flow_factory(_client_secret, *, scopes):
        handle = CHANNEL_HANDLES[len(selected)]
        return Flow(handle, scopes)

    authorized = authorize_all(
        home=tmp_path,
        flow_factory=flow_factory,
        service_factory=lambda credentials: Service(credentials.handle),
        output_fn=output.append,
    )

    assert authorized == CHANNEL_HANDLES
    assert selected == CHANNEL_HANDLES
    assert all((tmp_path / "tokens" / f"{handle}.json").is_file() for handle in CHANNEL_HANDLES)
    assert "fixture-secret-token" not in "\n".join(output)
    assert sum("Channels still needing authorization" in line for line in output) == 10


def test_authorization_does_not_save_token_for_wrong_account(tmp_path):
    (tmp_path / "tokens").mkdir()
    (tmp_path / "tokens" / "client_secret.json").write_text("{}", encoding="utf-8")
    output = []

    selections = iter(["@wrongchannel", "@expected"])

    class Flow:
        def __init__(self, _client_secret, scopes):
            assert scopes == SCOPES

        def run_local_server(self, **_kwargs):
            return CredentialsFixture(next(selections))

    class Service:
        def __init__(self, handle):
            self.handle = handle

        def channels(self):
            return self

        def list(self, **_kwargs):
            return self

        def execute(self):
            return {"items": [{"id": "channel-id", "snippet": {"customUrl": self.handle}}]}

    authorize_all(home=tmp_path, handles=["@expected"], flow_factory=Flow,
                  service_factory=lambda credentials: Service(credentials.handle), output_fn=output.append)
    assert (tmp_path / "tokens" / "@expected.json").is_file()
    assert not (tmp_path / "tokens" / "@wrongchannel.json").exists()
    assert "fixture-secret-token" not in "\n".join(output)
