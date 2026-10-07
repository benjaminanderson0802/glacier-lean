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


def test_pin_must_match_complete_version_token():
    catalog = valid_catalog()
    catalog["capabilities"][0]["version"] = "1.2.3"
    catalog["capabilities"][0]["install"] = "npx -y example-server@1.2.30"

    with pytest.raises(check.CatalogError, match="exact version or commit pin"):
        check.validate(catalog)


def test_docker_install_requires_digest():
    catalog = valid_catalog()
    catalog["capabilities"][0]["install"] = "docker run -i example/server:1.2.3"

    with pytest.raises(check.CatalogError, match="digest"):
        check.validate(catalog)


def test_docker_install_accepts_digest_pin():
    catalog = valid_catalog()
    catalog["capabilities"][0]["version"] = "sha256:" + "a" * 64
    catalog["capabilities"][0]["install"] = (
        "docker run -i example/server@sha256:" + "a" * 64
    )

    assert check.validate(catalog)


def test_network_allowlist_enforcement_must_match_declared_hosts():
    catalog = valid_catalog()
    catalog["capabilities"][0]["permissions"]["network_access"] = True
    catalog["capabilities"][0]["permissions"]["network_hosts"] = ["api.example.com"]
    catalog["capabilities"][0]["network_enforcement"] = "Enforced by host firewall: other.example.com"

    with pytest.raises(check.CatalogError, match="network enforcement"):
        check.validate(catalog)


def test_network_allowlist_requires_enforcement_declaration():
    catalog = valid_catalog()
    catalog["capabilities"][0]["permissions"]["network_access"] = True
    catalog["capabilities"][0]["permissions"]["network_hosts"] = ["api.example.com"]

    with pytest.raises(check.CatalogError, match="declared network host enforcement"):
        check.validate(catalog)


def test_version_pin_must_end_at_token_boundary():
    catalog = valid_catalog()
    catalog["capabilities"][0]["version"] = "1.2.3"
    catalog["capabilities"][0]["install"] = "npx -y example-server==1.2.30"

    with pytest.raises(check.CatalogError, match="exact version or commit pin"):
        check.validate(catalog)


def test_colon_version_pin_must_end_at_token_boundary():
    catalog = valid_catalog()
    catalog["capabilities"][0]["version"] = "1.2.3"
    catalog["capabilities"][0]["install"] = "docker run example/server:1.2.30@sha256:" + "a" * 64

    with pytest.raises(check.CatalogError, match="exact version or commit pin"):
        check.validate(catalog)
