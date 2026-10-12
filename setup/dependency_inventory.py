"""Read-only inventory of dependency declarations and venture lockfiles."""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any


_REQUIREMENT_NAME = re.compile(r"^\s*([A-Za-z0-9_.-]+)(?:\[[^]]+\])?\s*(.*)$")
_VERSION_SPECIFIER = re.compile(r"(?:===|==|~=|!=|<=|>=|<|>)")


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _entry_paths(display_path: str) -> dict[str, str]:
    venture_path = display_path.rsplit("/", 1)[0]
    return {"venture_path": venture_path, "manifest_path": display_path}


def _pip_status(specifier: str) -> str:
    specifier = specifier.split(";", 1)[0].strip()
    if not specifier:
        return "unpinned"
    if re.fullmatch(r"(?:===|==)\s*[^,\s]+", specifier):
        return "exact pin"
    if _VERSION_SPECIFIER.search(specifier):
        return "range"
    return "unpinned"


def _pip_entries(path: Path, display_path: str) -> list[dict[str, Any]]:
    entries = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        raw = line.strip()
        if not raw or raw.startswith("#") or raw.startswith(("--", "-f ", "-i ")):
            continue
        parse_line = re.sub(r"\s+#.*$", "", raw).strip()
        match = _REQUIREMENT_NAME.match(parse_line)
        if match:
            package, specifier = match.groups()
            status = _pip_status(specifier)
            version_specifier = specifier.split(";", 1)[0].strip() or "(no version specifier)"
        else:
            package = parse_line
            version_specifier = parse_line
            status = "unpinned"
        entries.append({
            "ecosystem": "pip",
            "package": package,
            "declared": raw,
            "specifier": version_specifier,
            "locked_version": None,
            "status": status,
            "provenance": "requirements manifest",
            "path": display_path,
            "line": line_number,
            **_entry_paths(display_path),
        })
    return entries


def _npm_package_name(lock_key: str) -> str | None:
    marker = "node_modules/"
    if marker not in lock_key:
        return None
    suffix = lock_key.rsplit(marker, 1)[1]
    parts = suffix.split("/")
    if not parts[0]:
        return None
    if parts[0].startswith("@") and len(parts) > 1:
        return "/".join(parts[:2])
    return parts[0]


def _npm_status(declared: str | None) -> str:
    if declared is None or not declared.strip():
        return "unknown"
    value = declared.strip()
    if value == "*":
        return "unpinned"
    if re.fullmatch(r"v?\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?", value):
        return "exact pin"
    if value.startswith(("^", "~", ">", "<", "=", "!")) or "*" in value or "||" in value:
        return "range"
    # Tags, git references, and URLs are not exact semver pins.
    return "unpinned"


def _npm_declarations(path: Path) -> dict[str, str]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    declarations: dict[str, str] = {}
    for section in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
        values = manifest.get(section, {})
        if isinstance(values, dict):
            declarations.update({str(name): str(spec) for name, spec in values.items()})
    return declarations


def _npm_entries(path: Path, display_path: str, manifest_path: Path | None = None) -> list[dict[str, Any]]:
    lock = json.loads(path.read_text(encoding="utf-8"))
    packages = lock.get("packages", {})
    root_package = packages.get("", {})
    root_declarations: dict[str, str] = {}
    if manifest_path is not None and manifest_path.is_file():
        root_declarations.update(_npm_declarations(manifest_path))
    for section in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
        declarations = root_package.get(section, {})
        if isinstance(declarations, dict):
            for name, spec in declarations.items():
                root_declarations.setdefault(str(name), str(spec))

    entries = []
    if not packages and isinstance(lock.get("dependencies"), dict):
        def visit_legacy(dependencies: dict[str, Any], parent_key: str = "") -> None:
            for package, package_record in dependencies.items():
                if not isinstance(package_record, dict):
                    continue
                version = package_record.get("version")
                if version is None:
                    continue
                direct = not parent_key and package in root_declarations
                lock_key = f"{parent_key}/node_modules/{package}" if parent_key else f"node_modules/{package}"
                entry: dict[str, Any] = {
                    "ecosystem": "npm",
                    "package": package,
                    "declared": root_declarations.get(package) if direct else None,
                    "locked_version": str(version),
                    "status": "locked exact",
                    "provenance": "direct lock" if direct else "transitive lock",
                    "path": display_path,
                    "lock_key": lock_key,
                    **_entry_paths(display_path),
                }
                if direct:
                    entry["declaration_status"] = _npm_status(entry["declared"])
                entries.append(entry)
                nested = package_record.get("dependencies", {})
                if isinstance(nested, dict):
                    visit_legacy(nested, lock_key)

        visit_legacy(lock["dependencies"])
        return entries

    for lock_key, package_record in packages.items():
        if not lock_key or not isinstance(package_record, dict):
            continue
        package = _npm_package_name(str(lock_key))
        version = package_record.get("version")
        if package is None or version is None:
            continue
        direct = str(lock_key) == f"node_modules/{package}" and package in root_declarations
        declared = root_declarations.get(package) if direct else None
        entry: dict[str, Any] = {
            "ecosystem": "npm",
            "package": package,
            "declared": declared,
            "locked_version": str(version),
            "status": "locked exact",
            "provenance": "direct lock" if direct else "transitive lock",
            "path": display_path,
            "lock_key": str(lock_key),
            **_entry_paths(display_path),
        }
        if direct:
            entry["declaration_status"] = _npm_status(declared)
        entries.append(entry)
    return entries


def inventory_venture_dependencies(ventures_dir: Path) -> dict[str, Any]:
    """Inventory existing venture requirements and npm locks without resolving packages."""
    ventures_dir = Path(ventures_dir)
    display_root = ventures_dir.name or "ventures"
    entries: list[dict[str, Any]] = []
    missing_files: list[str] = []
    missing_manifests: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []

    if not ventures_dir.is_dir():
        missing_files.append(display_root)
        return {"proposal_only": True, "entries": [], "missing_files": missing_files,
                "missing_manifests": missing_manifests, "errors": errors}

    for path in sorted(ventures_dir.rglob("requirements.txt")):
        display_path = f"{display_root}/{_relative(path, ventures_dir)}"
        try:
            entries.extend(_pip_entries(path, display_path))
        except (OSError, UnicodeError) as error:
            errors.append({"path": display_path, "error": str(error)})

    package_jsons = sorted(ventures_dir.rglob("package.json"))
    for package_json in package_jsons:
        lock_path = package_json.with_name("package-lock.json")
        package_display = f"{display_root}/{_relative(package_json, ventures_dir)}"
        try:
            declarations = _npm_declarations(package_json)
            if not lock_path.is_file():
                for package, declared in declarations.items():
                    entries.append({
                        "ecosystem": "npm",
                        "package": package,
                        "declared": declared,
                        "locked_version": None,
                        "status": _npm_status(declared),
                        "provenance": "package.json manifest (lock missing)",
                        "path": package_display,
                        **_entry_paths(package_display),
                    })
        except (json.JSONDecodeError, OSError, UnicodeError) as error:
            errors.append({"path": package_display, "error": str(error)})
        if not lock_path.is_file():
            lock_display = f"{display_root}/{_relative(lock_path, ventures_dir)}"
            missing_files.append(lock_display)
            missing_manifests.append({
                "path": lock_display,
                "venture_path": f"{display_root}/{_relative(package_json.parent, ventures_dir)}",
                "status": "missing",
            })

    for path in sorted(ventures_dir.rglob("package-lock.json")):
        display_path = f"{display_root}/{_relative(path, ventures_dir)}"
        try:
            entries.extend(_npm_entries(path, display_path, path.with_name("package.json")))
        except (json.JSONDecodeError, OSError, UnicodeError) as error:
            errors.append({"path": display_path, "error": str(error)})

    return {
        "proposal_only": True,
        "entries": entries,
        "missing_files": sorted(missing_files),
        "missing_manifests": sorted(missing_manifests, key=lambda item: item["path"]),
        "errors": errors,
    }
