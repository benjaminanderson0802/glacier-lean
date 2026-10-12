from __future__ import annotations

import json
import importlib
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ventures import install_all  # noqa: E402


def test_manifest_schema_accepts_contract_and_rejects_missing_owner_steps():
    schema = json.loads((ROOT / "ventures" / "venture.schema.json").read_text(encoding="utf-8"))
    valid = {
        "slug": "sample-venture", "name": "Sample venture", "flows": ["sample-flow"],
        "your_steps": [{"id": "approve-first", "title": "Approve first", "when": "Before launch",
                        "detail": "Review and approve the first customer-facing action."}],
    }
    jsonschema.validate(valid, schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({key: value for key, value in valid.items() if key != "your_steps"}, schema)


def test_all_checked_in_manifests_validate_against_one_schema():
    paths = sorted((ROOT / "ventures").glob("*/venture.json"))
    schema = json.loads((ROOT / "ventures" / "venture.schema.json").read_text(encoding="utf-8"))
    for path in paths:
        jsonschema.validate(json.loads(path.read_text(encoding="utf-8")), schema)


def test_installer_refuses_to_report_success_when_no_manifests_exist(tmp_path, monkeypatch):
    monkeypatch.setattr(install_all, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="no venture manifests found"):
        install_all.validate_all()


def test_installer_accepts_real_catalog_node_type_and_rejects_unknown_type(tmp_path, monkeypatch):
    venture = tmp_path / "sample-venture"
    (venture / "flows").mkdir(parents=True)
    manifest = {"slug": "sample-venture", "name": "Sample", "flows": ["sample-flow"], "your_steps": []}
    (venture / "venture.json").write_text(json.dumps(manifest), encoding="utf-8")
    flow_path = venture / "flows" / "sample-flow.json"
    flow = {"id": "sample-flow", "nodes": [{"id": "one", "type": "command", "config": {}}], "edges": []}
    flow_path.write_text(json.dumps(flow), encoding="utf-8")
    monkeypatch.setattr(install_all, "ROOT", tmp_path)
    assert install_all.validate_all() == [{"venture": "sample-venture", "flow": "sample-flow", "validated": True}]
    flow["nodes"][0]["type"] = "not-a-real-glacier-node"
    flow_path.write_text(json.dumps(flow), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown node type"):
        install_all.validate_all()


@pytest.mark.parametrize("module", ["customer", "filer", "mail", "connectors"])
def test_merged_blocks_import_from_ventures_package(module):
    imported = importlib.import_module(f"ventures.blocks.{module}")
    assert imported.__name__ == f"ventures.blocks.{module}"
