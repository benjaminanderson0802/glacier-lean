"""Contract checks for the registered CPSC products and approval waits."""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
VENTURE = ROOT / "ventures" / "cpsc-prep"


def load_installer():
    spec = importlib.util.spec_from_file_location("venture_installer", ROOT / "ventures" / "install_all.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_manifest_declares_broker_portal_batch_pricing_and_owner_steps():
    manifest = json.loads((VENTURE / "venture.json").read_text(encoding="utf-8"))
    assert manifest["product"]["broker_portal"]
    assert [entry["amount"] for entry in manifest["product"]["pricing"]["direct_batch"]] == [19, 29, 49]
    assert {step["id"] for step in manifest["your_steps"]} >= {"trade-lawyer-opinion", "customer-certification", "first-broker-contract"}
    assert all(name.startswith("reader.") or name.startswith("rules.") or name.startswith("feeds.") or name.startswith("customer.") or name.startswith("mail.") for name in manifest["block_functions"])


def test_broker_launch_flow_gates_contract_on_trade_lawyer_approval():
    flow = json.loads((VENTURE / "flows" / "cpsc-broker-launch.json").read_text(encoding="utf-8"))
    approvals = [node for node in flow["nodes"] if node["type"] == "approval"]
    assert len(approvals) == 2
    assert all(node["config"]["prompt"].startswith("Your step:") for node in approvals)
    assert "trade lawyer's written opinion" in approvals[0]["config"]["prompt"]
    assert "flat monthly fee" in approvals[1]["config"]["prompt"]
    edges = {(edge["source"], edge["target"], edge["label"]) for edge in flow["edges"]}
    assert ("lawyer-opinion", "first-contract", "yes") in edges
    assert ("first-contract", "ready", "yes") in edges


def test_installer_stages_scripts_and_keeps_workspace_data_separate(tmp_path):
    installer = load_installer()
    installer._stage_scripts(VENTURE, "cpsc-prep", tmp_path, ["cpsc-batch-prep"])
    staged = tmp_path / "workspaces" / "cpsc-batch-prep" / "ventures" / "cpsc-prep" / "scripts" / "cpsc_prep.py"
    assert staged.is_file()
    assert (VENTURE / "scripts" / "cpsc_prep.py").read_bytes() == staged.read_bytes()
    flow = json.loads((VENTURE / "flows" / "cpsc-batch-prep.json").read_text(encoding="utf-8"))
    runtime = installer._runtime_flow(flow, repo_root=ROOT, slug="cpsc-prep", home=tmp_path)
    command = next(node for node in runtime["nodes"] if node["id"] == "prepare-draft")
    assert command["config"]["cwd"] == str(tmp_path / "workspaces" / "cpsc-batch-prep" / "ventures" / "cpsc-prep")
    assert str(ROOT) in command["config"]["cmd"]
    assert "batch.json" in command["config"]["cmd"]


def test_status_board_is_per_importer_and_contains_no_source_documents(tmp_path):
    sys.path.insert(0, str(VENTURE / "scripts"))
    from status_board import record_result

    result_path = tmp_path / "result.json"
    result_path.write_text(json.dumps({
        "batch_id": "B-7",
        "importer_id": "IMPORTER-2",
        "status": "match",
        "products": [{"product_id": "SKU-1"}],
        "gaps": [],
        "source_documents": ["private-lab-report.pdf"],
    }), encoding="utf-8")
    status_path = record_result(result_path, tmp_path / "status")
    row = json.loads(status_path.read_text(encoding="utf-8"))
    assert status_path == tmp_path / "status" / "IMPORTER-2" / "B-7.json"
    assert row["product_count"] == 1
    assert row["submission_performed"] is False
    assert "source_documents" not in row


def test_direct_checkout_adapter_uses_test_link_and_never_charges(monkeypatch):
    sys.path.insert(0, str(VENTURE / "scripts"))
    block_package = types.ModuleType("ventures.blocks")
    calls = []
    fake_customer = types.SimpleNamespace(
        create_customer=lambda details: calls.append(("customer", details)) or {"id": "cus_test"},
        checkout_link=lambda plan: calls.append(("checkout", plan)) or "https://checkout.example.test/session",
        status_page=lambda customer_id: f"/status/{customer_id}",
        support_inbox=lambda: "local-test-inbox",
    )
    block_package.customer = fake_customer
    monkeypatch.setitem(sys.modules, "ventures.blocks", block_package)
    monkeypatch.setitem(sys.modules, "ventures.blocks.customer", fake_customer)
    from customer_portal import create_direct_checkout, customer_status_page, support_inbox

    result = create_direct_checkout({"name": "Importer Test"}, "direct_batch_standard")
    assert result["customer"] == {"id": "cus_test"}
    assert result["checkout"] == "https://checkout.example.test/session"
    assert result["mode"] == "test_until_owner_configures_live_key"
    assert calls == [("customer", {"name": "Importer Test"}), ("checkout", "direct_batch_standard")]
    assert customer_status_page("cus_test") == "/status/cus_test"
    assert support_inbox() == "local-test-inbox"
