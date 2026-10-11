from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ventures import install_all  # noqa: E402


class InstallAllTests(unittest.TestCase):
    def test_discovery_is_data_driven_and_only_filters_by_slug(self) -> None:
        all_flows = install_all.discover_flows()
        apify_flows = install_all.discover_flows("apify-tools")
        self.assertEqual(len(all_flows), len(apify_flows))
        self.assertEqual({flow["id"] for _, flow in apify_flows}, {
            "apify-ms-license-daily-canary",
            "apify-ms-license-your-step-publish",
        })

    def test_repository_working_directory_is_resolved_before_registration(self) -> None:
        flow = next(
            flow for _, flow in install_all.discover_flows("apify-tools")
            if flow["id"] == "apify-ms-license-daily-canary"
        )
        command = next(node for node in flow["nodes"] if node["type"] == "command")
        self.assertEqual(command["config"]["cwd"], str(ROOT))
        self.assertTrue(command["config"]["cmd"].startswith(install_all.python_command()))

    def test_only_missing_slug_fails_clearly(self) -> None:
        with self.assertRaisesRegex(ValueError, "No venture flows"):
            install_all.discover_flows("missing")

    def test_registration_uses_idempotent_put_and_install_token(self) -> None:
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                return b'{"saved": true, "commit": "abc"}'

        with patch("ventures.install_all.urlopen", return_value=Response()) as open_url:
            result = install_all.install_flow(
                {"id": "apify-flow", "nodes": [], "edges": []},
                base="http://localhost:8000/api",
                token="local-token",
            )
        self.assertEqual(result["commit"], "abc")
        request = open_url.call_args.args[0]
        self.assertEqual(request.method, "PUT")
        self.assertEqual(request.get_header("Authorization"), "Bearer local-token")


if __name__ == "__main__":
    unittest.main()
