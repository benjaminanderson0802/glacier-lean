#!/usr/bin/env python3
"""Validate and display Glacier's reviewed MCP capability catalog."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CATALOG = Path(__file__).resolve().parents[2] / "glacier" / "contract" / "capabilities.yaml"

# SPDX identifiers that are OSI-approved permissive or weak-copyleft licenses.
OSI_LICENSES = {
    "0BSD",
    "Apache-2.0",
    "Artistic-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "EPL-2.0",
    "ISC",
    "MIT",
    "MPL-2.0",
    "PostgreSQL",
    "Python-2.0",
    "Zlib",
}
REQUIRED_FIELDS = {
    "name",
    "description",
    "source",
    "license",
    "version",
    "install",
    "permissions",
    "risk_notes",
    "reviewed_by",
    "reviewed_on",
}
PERMISSION_FIELDS = {"files", "network_access", "network_hosts", "secrets"}
VERSION_RE = re.compile(r"^v?\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
COMMIT_RE = re.compile(r"^[0-9a-fA-F]{40}$")


class CatalogError(ValueError):
    """Raised when a catalog is incomplete or unsafe to offer."""


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate(document: Any) -> list[dict[str, Any]]:
    if not isinstance(document, dict) or set(document) != {"capabilities"}:
        raise CatalogError("Catalog must contain only a 'capabilities' list.")
    entries = document["capabilities"]
    if not isinstance(entries, list) or not entries:
        raise CatalogError("Catalog must contain at least one capability.")

    rows = []
    names = set()
    for number, entry in enumerate(entries, start=1):
        label = f"Capability {number}"
        if not isinstance(entry, dict):
            raise CatalogError(f"{label} must be a mapping.")
        missing = REQUIRED_FIELDS - entry.keys()
        if missing:
            raise CatalogError(f"{label} is missing required fields: {', '.join(sorted(missing))}.")

        for field in REQUIRED_FIELDS - {"permissions", "reviewed_on"}:
            if not _nonempty(entry[field]):
                raise CatalogError(f"{label} field '{field}' must be plain text.")
        if entry["name"] in names:
            raise CatalogError(f"Duplicate capability name: {entry['name']}.")
        names.add(entry["name"])

        if entry["license"] not in OSI_LICENSES:
            raise CatalogError(f"{entry['name']} license must be an OSI-approved license.")
        pin = entry["version"].strip()
        if pin.lower() in {"latest", "main", "master", "stable", "*"} or not (
            VERSION_RE.fullmatch(pin) or COMMIT_RE.fullmatch(pin)
        ):
            raise CatalogError(f"{entry['name']} needs an exact version or commit pin.")
        if not entry["source"].startswith("https://"):
            raise CatalogError(f"{entry['name']} source must be an HTTPS repository URL.")
        if "@latest" in entry["install"].lower() or re.search(r"\b(latest|main|master)\b", entry["install"], re.I):
            raise CatalogError(f"{entry['name']} install command must use its exact pin.")
        normalized_pin = pin.removeprefix("v")
        if pin not in entry["install"] and normalized_pin not in entry["install"]:
            raise CatalogError(f"{entry['name']} install command must include its exact version or commit pin.")

        permissions = entry["permissions"]
        if not isinstance(permissions, dict) or set(permissions) != PERMISSION_FIELDS:
            raise CatalogError(
                f"{entry['name']} permissions must declare files, network_access, network_hosts, and secrets."
            )
        for field in ("files", "network_hosts", "secrets"):
            values = permissions[field]
            if not isinstance(values, list) or any(not _nonempty(value) for value in values):
                raise CatalogError(f"{entry['name']} permission '{field}' must be a list of plain text values.")
        if not isinstance(permissions["network_access"], bool):
            raise CatalogError(f"{entry['name']} permission 'network_access' must be true or false.")
        if permissions["network_access"] and not permissions["network_hosts"]:
            raise CatalogError(f"{entry['name']} network access must name at least one allowed network host.")
        if not permissions["network_access"] and permissions["network_hosts"]:
            raise CatalogError(f"{entry['name']} lists network hosts while network access is disabled.")

        try:
            reviewed_on = date.fromisoformat(str(entry["reviewed_on"]))
        except ValueError as error:
            raise CatalogError(f"{entry['name']} reviewed_on must be an ISO date (YYYY-MM-DD).") from error
        rows.append({"name": entry["name"], "version": pin, "license": entry["license"], "reviewed_on": reviewed_on.isoformat()})
    return rows


def load_catalog(path: Path) -> Any:
    try:
        with path.open(encoding="utf-8") as stream:
            return yaml.safe_load(stream)
    except OSError as error:
        raise CatalogError(f"Cannot read catalog '{path}': {error}") from error
    except yaml.YAMLError as error:
        raise CatalogError(f"Catalog YAML is not valid: {error}") from error


def print_table(rows: list[dict[str, Any]]) -> None:
    headers = ("Name", "Pinned version / commit", "License", "Reviewed")
    values = [[row["name"], row["version"], row["license"], row["reviewed_on"]] for row in rows]
    widths = [max(len(headers[i]), *(len(row[i]) for row in values)) for i in range(len(headers))]
    print(" | ".join(headers[i].ljust(widths[i]) for i in range(len(headers))))
    print("-+-".join("-" * width for width in widths))
    for row in values:
        print(" | ".join(row[i].ljust(widths[i]) for i in range(len(headers))))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalog", nargs="?", type=Path, default=DEFAULT_CATALOG)
    args = parser.parse_args(argv)
    try:
        rows = validate(load_catalog(args.catalog))
    except CatalogError as error:
        print(f"Catalog check failed: {error}", file=sys.stderr)
        return 1
    print_table(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
