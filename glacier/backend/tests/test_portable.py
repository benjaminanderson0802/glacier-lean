import json

import pytest

from glacier.backend.portable import export_flow, import_flow


def sample_flow():
    return {
        "id": "nightly-tests",
        "name": "Nightly tests",
        "nodes": [
            {"id": "start", "type": "schedule", "config": {"cron": "*/5 * * * *"}, "position": {"x": 0, "y": 0}},
            {"id": "check", "type": "check", "config": {"expr": "exit_code == 0"}, "position": {"x": 1, "y": 0}},
        ],
        "edges": [
            {"id": "e1", "source": "start", "target": "check", "label": ""},
        ],
        "max_steps": 500,
    }


def test_export_import_round_trip_equals_input():
    flow = sample_flow()

    exported = export_flow(flow)
    envelope = json.loads(exported)

    assert list(envelope) == ["glacier_flow", "exported_at", "flow"]
    assert envelope["glacier_flow"] == 1
    assert "T" in envelope["exported_at"]
    assert exported.splitlines()[0] == "{"
    assert "  \"glacier_flow\": 1," in exported
    assert import_flow(exported, set()) == flow


def test_unknown_node_type_names_node_in_error():
    flow = sample_flow()
    flow["nodes"][0]["type"] = "not-a-real-node"

    with pytest.raises(ValueError, match="start"):
        import_flow(json.dumps({"glacier_flow": 1, "flow": flow}), set())


def test_edge_to_missing_node_is_rejected():
    flow = sample_flow()
    flow["edges"][0]["target"] = "missing"

    with pytest.raises(ValueError, match="e1"):
        import_flow(json.dumps({"glacier_flow": 1, "flow": flow}), set())


def test_bad_branch_label_is_rejected():
    flow = sample_flow()
    flow["nodes"].append({"id": "approval", "type": "approval", "config": {}, "position": {}})
    flow["edges"].append({"id": "e2", "source": "approval", "target": "check", "label": "maybe"})

    with pytest.raises(ValueError, match="e2"):
        import_flow(json.dumps({"glacier_flow": 1, "flow": flow}), set())


def test_decide_option_edge_labels_are_accepted():
    flow = {
        "id": "triage",
        "name": "Triage",
        "nodes": [
            {"id": "decider", "type": "decide", "config": {"options": "Billing, Tech support, Other"}},
            {"id": "billing", "type": "note", "config": {}},
        ],
        "edges": [
            {"id": "e1", "source": "decider", "target": "billing", "label": "Billing"},
        ],
    }

    assert import_flow(json.dumps({"glacier_flow": 1, "flow": flow}), set()) == flow


def test_id_clash_renames_flow_and_suffixes_name():
    flow = sample_flow()

    imported = import_flow(json.dumps({"glacier_flow": 1, "flow": flow}), {"nightly-tests", "nightly-tests-2"})

    assert imported["id"] == "nightly-tests-3"
    assert imported["name"] == "Nightly tests (copy)"
    assert flow["id"] == "nightly-tests"
    assert flow["name"] == "Nightly tests"


@pytest.mark.parametrize("envelope", [{"flow": {}}, {"glacier_flow": 2, "flow": {}}])
def test_wrong_or_missing_version_is_rejected(envelope):
    with pytest.raises(ValueError, match="version"):
        import_flow(json.dumps(envelope), set())


def test_non_json_has_friendly_error():
    with pytest.raises(ValueError, match="valid JSON"):
        import_flow("this is not a flow file", set())
