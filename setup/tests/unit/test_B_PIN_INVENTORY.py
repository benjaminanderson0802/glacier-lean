from __future__ import annotations

import json

from setup.dependency_inventory import inventory_venture_dependencies
from setup import health_check


def test_inventory_reports_pip_specs_npm_lock_provenance_and_missing_lock(tmp_path):
    ventures = tmp_path / "ventures"
    pip_dir = ventures / "blocks" / "sample-pip"
    pip_dir.mkdir(parents=True)
    pip_manifest = pip_dir / "requirements.txt"
    pip_manifest.write_text(
        "pinned-lib==1.2.3\nrange-lib>=2.0,<3\nunpinned-lib\n",
        encoding="utf-8",
    )

    npm_dir = ventures / "sample-npm"
    npm_dir.mkdir()
    npm_manifest = npm_dir / "package.json"
    npm_manifest.write_text(
        json.dumps({"dependencies": {"direct-range": "^2.0.0", "direct-pin": "1.0.0"}}),
        encoding="utf-8",
    )
    npm_lock = npm_dir / "package-lock.json"
    npm_lock.write_text(
        json.dumps({
            "lockfileVersion": 3,
            "packages": {
                "": {"dependencies": {"direct-range": "^2.0.0", "direct-pin": "1.0.0"}},
                "node_modules/direct-range": {"version": "2.4.0"},
                "node_modules/direct-pin": {"version": "1.0.0"},
                "node_modules/transitive-lib": {"version": "3.1.4"},
            },
        }),
        encoding="utf-8",
    )

    missing_dir = ventures / "missing-lock"
    missing_dir.mkdir()
    (missing_dir / "package.json").write_text(
        json.dumps({"dependencies": {"no-lock": "*"}}), encoding="utf-8"
    )

    before = {path: path.read_bytes() for path in (pip_manifest, npm_manifest, npm_lock)}
    inventory = inventory_venture_dependencies(ventures)
    after = {path: path.read_bytes() for path in (pip_manifest, npm_manifest, npm_lock)}
    by_package = {entry["package"]: entry for entry in inventory["entries"]}

    assert by_package["pinned-lib"]["status"] == "exact pin"
    assert by_package["pinned-lib"]["declared"] == "pinned-lib==1.2.3"
    assert by_package["pinned-lib"]["specifier"] == "==1.2.3"
    assert by_package["pinned-lib"]["path"] == "ventures/blocks/sample-pip/requirements.txt"
    assert by_package["pinned-lib"]["venture_path"] == "ventures/blocks/sample-pip"
    assert by_package["pinned-lib"]["manifest_path"] == "ventures/blocks/sample-pip/requirements.txt"
    assert by_package["range-lib"]["status"] == "range"
    assert by_package["unpinned-lib"]["status"] == "unpinned"
    assert by_package["direct-range"]["status"] == "locked exact"
    assert by_package["direct-range"]["declared"] == "^2.0.0"
    assert by_package["direct-range"]["locked_version"] == "2.4.0"
    assert by_package["transitive-lib"]["provenance"] == "transitive lock"
    assert by_package["transitive-lib"]["path"] == "ventures/sample-npm/package-lock.json"
    assert by_package["no-lock"]["status"] == "unpinned"
    assert by_package["no-lock"]["locked_version"] is None
    assert by_package["no-lock"]["provenance"] == "package.json manifest (lock missing)"
    assert inventory["missing_files"] == ["ventures/missing-lock/package-lock.json"]
    assert inventory["missing_manifests"] == [{
        "path": "ventures/missing-lock/package-lock.json",
        "venture_path": "ventures/missing-lock",
        "status": "missing",
    }]
    assert after == before


def test_inventory_missing_ventures_directory_is_reported(tmp_path):
    inventory = inventory_venture_dependencies(tmp_path / "ventures")

    assert inventory["entries"] == []
    assert inventory["missing_files"] == ["ventures"]


def test_inventory_reads_nested_transitive_entries_from_legacy_npm_lock(tmp_path):
    venture = tmp_path / "ventures" / "legacy-npm"
    venture.mkdir(parents=True)
    (venture / "package.json").write_text(
        json.dumps({"dependencies": {"direct": "1.0.0"}}), encoding="utf-8"
    )
    (venture / "package-lock.json").write_text(
        json.dumps({"lockfileVersion": 1, "dependencies": {
            "direct": {"version": "1.0.0", "dependencies": {
                "nested": {"version": "2.3.4"},
            }},
        }}),
        encoding="utf-8",
    )

    inventory = inventory_venture_dependencies(tmp_path / "ventures")
    by_package = {entry["package"]: entry for entry in inventory["entries"]}

    assert by_package["direct"]["provenance"] == "direct lock"
    assert by_package["nested"]["provenance"] == "transitive lock"
    assert by_package["nested"]["locked_version"] == "2.3.4"


def test_health_report_embeds_inventory_and_prints_unpinned_provenance(monkeypatch, tmp_path, capsys):
    ventures = tmp_path / "ventures" / "sample"
    ventures.mkdir(parents=True)
    (ventures / "requirements.txt").write_text("loose-package\n", encoding="utf-8")
    monkeypatch.setattr(health_check, "REPO", tmp_path)
    monkeypatch.setattr(health_check, "run_health_sections", lambda quick: [])
    monkeypatch.setattr(health_check, "check_upgrades", lambda python=None: ([], "proposals only"))
    report_path = tmp_path / "report.json"

    code = health_check.main(["--quick", "--report", str(report_path)])

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert code == 0
    assert report["venture_dependencies"]["entries"][0]["package"] == "loose-package"
    assert "ventures/sample/requirements.txt" in capsys.readouterr().out
