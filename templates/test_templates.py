"""Acceptance checks for the starter flow gallery."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
CATALOG = ROOT.parent / "glacier" / "contract" / "node_types.json"
EXPECTED_IDS = {
    "tpl-daily-report",
    "tpl-website-monitor",
    "tpl-test-and-fix",
    "tpl-weekly-research",
    "tpl-folder-cleanup",
    "tpl-inbox-triage",
    "tpl-folder-backup",
    "tpl-sub-flow-example",
    "tpl-nightly-job",
    "tpl-explain-error",
    # six everyday templates added later; each carries its own acceptance check
    "tpl-document-note",
    "tpl-downloads-tidy",
    "tpl-meeting-tasks",
    "tpl-web-change-watch",
    "tpl-morning-brief",
    "tpl-backup-check",
}
EVERYDAY_IDS = {"tpl-document-note", "tpl-downloads-tidy", "tpl-meeting-tasks",
                "tpl-web-change-watch", "tpl-morning-brief", "tpl-backup-check"}
DESTRUCTIVE_COMMAND = re.compile(
    r"(?:^|[;&|]\s*)(?:sudo\s+)?(?:rm|rmdir|shred|unlink)\b"
    r"|\bfind\b[^\n]*\s-delete\b|(?:^|\s)-exec\s+rm\b"
    r"|\bxargs\s+rm\b|\bmv\s+|\btruncate\b|\bgit\s+clean\b",
    re.IGNORECASE,
)


def load_catalog():
    """Core step types plus the step plug-ins shipped in glacier/backend/nodes (same catalog the screen gets)."""
    import importlib.util
    import sys
    types = json.loads(CATALOG.read_text(encoding="utf-8"))["types"]
    backend = ROOT.parent / "glacier" / "backend"
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))
    for path in sorted((backend / "nodes").glob("*.py")):
        spec = importlib.util.spec_from_file_location(f"_tpl_check_{path.stem}", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        catalog = getattr(module, "NODE", {}).get("catalog") if isinstance(getattr(module, "NODE", None), dict) else None
        if isinstance(catalog, dict) and catalog.get("type"):
            types.append(catalog)
    return types


def load_templates():
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(ROOT.glob("*.json"))]


def test_gallery_has_the_sixteen_requested_templates():
    templates = load_templates()
    assert len(templates) == 16
    assert {template["id"] for template in templates} == EXPECTED_IDS


def test_templates_follow_the_environment_contract_and_catalog():
    catalog = {item["type"]: item for item in load_catalog()}
    templates = load_templates()
    ids = [template["id"] for template in templates]
    assert len(ids) == len(set(ids))

    for template in templates:
        assert set(template) <= {"id", "name", "nodes", "edges", "max_steps",
                                 "goal", "acceptance", "description", "when_to_use"}
        if template["id"] in EVERYDAY_IDS:
            assert template.get("goal") and template.get("acceptance"), template["id"]
        assert template["id"].startswith("tpl-")
        assert template["name"].strip()
        assert "_" not in template["name"]
        assert template["nodes"]

        node_ids = [node["id"] for node in template["nodes"]]
        assert len(node_ids) == len(set(node_ids))
        known_node_ids = set(node_ids)
        nodes_by_id = {node["id"]: node for node in template["nodes"]}
        for node in template["nodes"]:
            assert node["type"] in catalog
            assert set(node["config"]) <= {
                field["key"] for field in catalog[node["type"]]["fields"]
            }
            assert set(node["position"]) >= {"x", "y"}
            assert all(isinstance(node["position"][axis], (int, float)) for axis in ("x", "y"))
            assert node["position"]["x"] % 260 == 0
            assert node["position"]["y"] % 140 == 0

        edge_ids = [edge["id"] for edge in template["edges"]]
        assert len(edge_ids) == len(set(edge_ids))
        for edge in template["edges"]:
            assert edge["source"] in known_node_ids
            assert edge["target"] in known_node_ids
            label = edge.get("label", "")
            if label:
                source = nodes_by_id[edge["source"]]
                source_type = catalog[source["type"]]
                if source_type.get("branches"):
                    allowed = {value.casefold() for value in source_type["branches"]}
                elif source_type.get("branches_from") == "options":
                    allowed = {
                        value.strip().casefold()
                        for value in source["config"]["options"].split(",")
                    }
                else:
                    allowed = set()
                assert label.casefold() in allowed


def test_commands_are_safe_linux_commands_without_folder_placeholders():
    for template in load_templates():
        for node in template["nodes"]:
            if node["type"] != "command":
                continue
            command = node["config"]["cmd"]
            assert not DESTRUCTIVE_COMMAND.search(command), (template["id"], command)
            assert "<" not in command and ">" not in command


def test_every_write_enabled_codex_step_requires_an_approval_yes_edge():
    for template in load_templates():
        nodes = {node["id"]: node for node in template["nodes"]}
        approvals = {node_id for node_id, node in nodes.items() if node["type"] == "approval"}
        writable = {
            node_id for node_id, node in nodes.items()
            if node["type"] == "codex"
            and node["config"].get("sandbox", "workspace-write")
            in {"workspace-write", "danger-full-access"}
        }
        if not writable:
            continue
        outgoing = {}
        for edge in template["edges"]:
            outgoing.setdefault(edge["source"], []).append(edge)
        starts = {node_id for node_id in nodes if not any(e["target"] == node_id for e in template["edges"])}
        pending = [(node_id, False) for node_id in starts]
        visited = set()
        while pending:
            node_id, approved = pending.pop()
            state = (node_id, approved)
            if state in visited:
                continue
            visited.add(state)
            assert node_id not in writable or approved, (template["id"], node_id)
            for edge in outgoing.get(node_id, []):
                next_approved = approved or (
                    node_id in approvals and edge.get("label", "").casefold() == "yes"
                )
                pending.append((edge["target"], next_approved))


def test_required_flow_patterns_are_present():
    templates = {template["id"]: template for template in load_templates()}

    monitor = templates["tpl-website-monitor"]
    monitor_nodes = {node["id"]: node for node in monitor["nodes"]}
    assert any(node["type"] == "approval" for node in monitor_nodes.values())
    assert any(node["type"] == "command" and "curl" in node["config"]["cmd"] for node in monitor_nodes.values())

    repair = templates["tpl-test-and-fix"]
    repair_nodes = [node for node in repair["nodes"]]
    assert any(node["type"] == "loop" and node["config"].get("times") == "3" for node in repair_nodes)
    assert any(node["type"] == "check" and node["config"].get("expr") == "exit_code == 0" for node in repair_nodes)
    assert any(node["type"] == "codex" for node in repair_nodes)
    assert any(node["type"] == "approval" for node in repair_nodes)
    repair_commands = [node["config"]["cmd"] for node in repair_nodes if node["type"] == "command"]
    assert all(not command.startswith("cd ") for command in repair_commands)

    triage = templates["tpl-inbox-triage"]
    decide = next(node for node in triage["nodes"] if node["type"] == "decide")
    options = {value.strip().casefold() for value in decide["config"]["options"].split(",")}
    assert len(options) == 3

    cleanup = templates["tpl-folder-cleanup"]
    cleanup_nodes = {node["id"]: node for node in cleanup["nodes"]}
    approval_ids = {key for key, node in cleanup_nodes.items() if node["type"] == "approval"}
    mutating_nodes = {
        key for key, node in cleanup_nodes.items()
        if node["type"] == "codex" and any(word in node["config"]["prompt"].casefold() for word in ("move", "delete", "remove", "rename"))
    }
    assert approval_ids
    assert mutating_nodes
    move_prompt = cleanup_nodes["move_files"]["config"]["prompt"]
    assert "{prev_output}" in move_prompt
    assert "only the files listed there" in move_prompt.casefold()
    assert all(
        any(edge["source"] in approval_ids and edge["label"].casefold() == "yes" and edge["target"] == mutation for edge in cleanup["edges"])
        for mutation in mutating_nodes
    )

    backup = templates["tpl-folder-backup"]
    backup_commands = [node["config"]["cmd"] for node in backup["nodes"] if node["type"] == "command"]
    assert all(not command.startswith("cd ") for command in backup_commands)
    assert any('d="$GLACIER_HOME/backups/tpl-folder-backup/$(date +%F)"' in command and "cp -a . \"$d\"" in command for command in backup_commands)
    assert any("diff -qr . \"$d\"" in command for command in backup_commands)
    assert any(node["type"] == "check" for node in backup["nodes"])

    sub_flow = templates["tpl-sub-flow-example"]
    flow = next(node for node in sub_flow["nodes"] if node["type"] == "flow")
    assert flow["config"]["env"] == "tpl-daily-report"

    nightly = templates["tpl-nightly-job"]
    schedule = next(node for node in nightly["nodes"] if node["type"] == "schedule")
    command = next(node for node in nightly["nodes"] if node["type"] == "command")
    assert schedule["config"]["cron"] == "0 2 * * *"
    assert int(command["config"]["retries"]) > 0
    assert int(command["config"]["timeout"]) > 0

    explain = templates["tpl-explain-error"]
    assert any(node["type"] == "codex" for node in explain["nodes"])
    assert any(node["type"] == "note" for node in explain["nodes"])


def test_daily_report_prompt_uses_the_previous_step_output():
    report = next(t for t in load_templates() if t["id"] == "tpl-daily-report")
    codex = next(node for node in report["nodes"] if node["type"] == "codex")
    assert "{prev_output}" in codex["config"]["prompt"]
