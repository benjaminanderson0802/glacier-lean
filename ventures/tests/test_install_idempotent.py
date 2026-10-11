from __future__ import annotations

import json
from unittest.mock import patch

from ventures import install_all


def test_unchanged_flow_install_skips_a_new_environment_revision() -> None:
    flow = {"id": "apify-flow", "name": "Daily check", "nodes": [], "edges": []}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            return json.dumps(flow).encode("utf-8")

    with patch("ventures.install_all.urlopen", return_value=Response()) as open_url:
        result = install_all.register_flow_if_changed("http://localhost:8000", "local-token", flow)

    assert result == {"saved": False, "unchanged": True}
    assert open_url.call_count == 1
    assert open_url.call_args.args[0].get_method() == "GET"
