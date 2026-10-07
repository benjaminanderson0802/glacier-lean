"""Acceptance tests for the reviewed MCP capability catalog."""

import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).with_name("check.py")
spec = importlib.util.spec_from_file_location("catalog_check", MODULE_PATH)
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


def valid_catalog():
    return {
        "capabilities": [
            {
                "name": "Example server",
                "description": "Lets a worker read an approved local folder.",
                "source": "https://github.com/example/server",
                "license": "MIT",
                "version": "v1.2.3",
                "install": "npx -y example-server@1.2.3",
                "permissions": {
                    "files": ["workspace:read"],
                    "network_access": False,
                    "network_hosts": [],
                    "secrets": [],
                },
                "risk_notes": "Can expose files under the approved folder.",
                "reviewed_by": "Glacier security review",
                "reviewed_on": "2026-10-07",
            }
        ]
    }


def test_valid_catalog_passes_and_prints_table(capsys):
    rows = check.validate(valid_catalog())
    check.print_table(rows)

    assert len(rows) == 1
    assert "Example server" in capsys.readouterr().out


def test_missing_pin_fails():
    catalog = valid_catalog()
    catalog["capabilities"][0]["version"] = "latest"

    with pytest.raises(check.CatalogError, match="exact version or commit"):
        check.validate(catalog)


def test_non_osi_license_fails():
    catalog = valid_catalog()
    catalog["capabilities"][0]["license"] = "Business Source License"

    with pytest.raises(check.CatalogError, match="OSI-approved"):
        check.validate(catalog)


def test_network_access_without_host_allowlist_fails():
    catalog = valid_catalog()
    permissions = catalog["capabilities"][0]["permissions"]
    permissions["network_access"] = True
    permissions["network_hosts"] = []

    with pytest.raises(check.CatalogError, match="allowed network host"):
        check.validate(catalog)


def test_install_command_must_match_pin():
    catalog = valid_catalog()
    catalog["capabilities"][0]["install"] = "npx -y example-server@latest"

    with pytest.raises(check.CatalogError, match="exact pin"):
        check.validate(catalog)
