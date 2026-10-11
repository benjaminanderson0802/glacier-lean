from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
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
        manifest = json.loads((ROOT / "ventures" / "apify-tools" / "venture.json").read_text(encoding="utf-8"))
        self.assertEqual({flow["id"] for _, flow in apify_flows}, set(manifest["flows"]))
        self.assertLess(len(apify_flows), len(all_flows))

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

    def test_c_flow_asset_staging_runs_from_disposable_workspace_without_checkout(self) -> None:
        cases = (
            ("property-tax", "property-tax-prepare-packet", "property_tax.py"),
            ("carpenter-goods", "carpenter-prepare-listing", "listing_prep.py"),
        )
        for slug, flow_id, script_name in cases:
            with self.subTest(venture=slug):
                flow = json.loads(
                    (ROOT / "ventures" / slug / "flows" / f"{flow_id}.json").read_text()
                )
                with tempfile.TemporaryDirectory(prefix="c-flow-assets-") as temp:
                    home = Path(temp) / "disposable-home"
                    flow_workspace = home / "workspaces" / flow["id"]
                    flow_workspace.mkdir(parents=True)

                    registered = []

                    def capture_registration(_api: str, _token: str, runtime: dict) -> dict:
                        registered.append(runtime)
                        return {"saved": True}

                    with patch.object(
                        install_all, "register_flow_if_changed", side_effect=capture_registration
                    ):
                        install_all.install(
                            "http://127.0.0.1:8000", "test-token", only=slug, home=home
                        )

                    runtime = next(item for item in registered if item["id"] == flow["id"])
                    command = next(
                        node for node in runtime["nodes"] if node["type"] == "command"
                    )["config"]
                    script = flow_workspace / "ventures" / slug / "scripts" / script_name

                    self.assertTrue(script.is_file())
                    self.assertEqual(command["cwd"], ".")
                    self.assertNotIn(str(ROOT), command["cmd"])
                    self.assertTrue(script.resolve().is_relative_to(flow_workspace.resolve()))

                    env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
                    env["GLACIER_HOME"] = str(home)
                    result = subprocess.run(
                        command["cmd"] + " --help",
                        cwd=flow_workspace,
                        env=env,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)

    def test_c_flow_asset_staging_rejects_a_destination_symlink_outside_workspace(self) -> None:
        with tempfile.TemporaryDirectory(prefix="c-flow-stage-boundary-") as temp:
            root = Path(temp)
            workspace = root / "workspace"
            source = root / "source"
            outside = root / "outside"
            source.mkdir()
            workspace.mkdir()
            outside.mkdir()
            (source / "script.py").write_text("print('ok')\n", encoding="utf-8")
            try:
                (workspace / "ventures").symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"directory symlinks unavailable: {exc}")

            with self.assertRaisesRegex(ValueError, "escapes its staging root"):
                install_all._copy_runtime_assets(
                    source,
                    workspace / "ventures" / "sample" / "scripts",
                    staging_root=workspace,
                )


if __name__ == "__main__":
    unittest.main()
