"""Portable, validated JSON export and import for Glacier flows."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


_NODE_TYPES_PATH = Path(__file__).resolve().parents[1] / "contract" / "node_types.json"


def _agents_md(flow: dict) -> str:
    """Describe a flow in plain words for another coding agent."""
    lines = [f"# {flow.get('name') or flow.get('id') or 'Glacier automation'}", ""]
    goal = flow.get("goal") or flow.get("description")
    if goal:
        lines.extend(["## Goal", "", str(goal), ""])
    else:
        lines.extend(["## Goal", "", f"Run the {flow.get('name') or 'automation'} steps below.", ""])

    lines.extend(["## Steps", ""])
    labels = {
        "command": "Run a command", "codex": "Ask Codex", "acp_agent": "Ask a coding agent",
        "local_ai": "Ask a local AI model", "check": "Check a result", "approval": "Wait for approval",
        "note": "Save a note", "schedule": "Start on a schedule", "decide": "Choose an option",
        "loop": "Repeat steps", "flow": "Run another automation",
    }
    for node in flow.get("nodes", []):
        if not isinstance(node, dict):
            continue
        kind = str(node.get("type") or "step")
        name = str(node.get("name") or node.get("id") or labels.get(kind, kind.replace("_", " ")))
        config = node.get("config") if isinstance(node.get("config"), dict) else {}
        description = node.get("description")
        if not description:
            if kind in {"codex", "acp_agent", "local_ai"}:
                description = config.get("prompt")
            elif kind == "command":
                description = config.get("cmd")
            elif kind == "check":
                description = config.get("expr")
            elif kind == "note":
                description = config.get("path")
            elif kind == "schedule":
                description = config.get("cron")
        lines.append(f"- {name}: {description or labels.get(kind, 'Run this step').rstrip('.')}.")

    checks = []
    for node in flow.get("nodes", []):
        if isinstance(node, dict) and node.get("type") == "check":
            expr = (node.get("config") or {}).get("expr")
            if expr:
                checks.append(f"- The step check must pass: `{expr}`.")
    for check in flow.get("acceptance", []) if isinstance(flow.get("acceptance"), list) else []:
        if isinstance(check, dict):
            summary = check.get("description") or check.get("command") or check.get("schema") or check.get("kind")
            if summary:
                checks.append(f"- The acceptance check must pass: {summary}.")
    lines.extend(["", "## Checks", ""])
    lines.extend(checks or ["- Confirm that each step completed successfully."])
    return "\n".join(lines) + "\n"


def export_flow(flow: dict, *, include_agents_md: bool = False) -> str:
    """Return a readable, versioned flow file; optionally include AGENTS.md guidance."""
    package = {
        "glacier_flow": 1,
        "exported_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "flow": flow,
    }
    if include_agents_md:
        package["agents_md"] = _agents_md(flow)
    return json.dumps(package, indent=2, ensure_ascii=False) + "\n"


def import_flow(text: str, existing_ids: set[str]) -> dict:
    """Read and validate a portable flow file, renaming an existing flow id."""
    try:
        package = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("This file is not valid JSON. Choose a Glacier flow file.") from exc

    if not isinstance(package, dict) or package.get("glacier_flow") != 1 or isinstance(package.get("glacier_flow"), bool):
        raise ValueError("This file has a missing or unsupported Glacier flow version.")
    flow = package.get("flow")
    _validate_flow(flow)

    imported = deepcopy(flow)
    flow_id = imported.get("id")
    if flow_id in existing_ids:
        suffix = 2
        while f"{flow_id}-{suffix}" in existing_ids:
            suffix += 1
        imported["id"] = f"{flow_id}-{suffix}"
        imported["name"] = f"{imported.get('name', '')} (copy)"
    return imported


def _validate_flow(flow: Any) -> None:
    if not isinstance(flow, dict):
        raise ValueError("The flow is missing or is not an object.")

    flow_id = flow.get("id")
    if not isinstance(flow_id, str) or not flow_id.strip():
        raise ValueError("The flow needs a non-empty id.")

    nodes = flow.get("nodes")
    edges = flow.get("edges")
    if not isinstance(nodes, list):
        raise ValueError("The flow's nodes must be a list.")
    if not isinstance(edges, list):
        raise ValueError("The flow's edges must be a list.")

    try:
        with _NODE_TYPES_PATH.open(encoding="utf-8") as source:
            definitions = json.load(source)["types"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValueError("Glacier could not read its node type definitions.") from exc
    node_types = {definition["type"]: definition for definition in definitions}

    nodes_by_id: dict[str, dict] = {}
    for index, node in enumerate(nodes, start=1):
        node_name = node.get("id") if isinstance(node, dict) else None
        display_id = node_name if isinstance(node_name, str) else f"number {index}"
        if not isinstance(node, dict):
            raise ValueError(f"Node {display_id} must be an object.")
        if not isinstance(node_name, str) or not node_name:
            raise ValueError(f"Node {display_id} needs an id.")
        if node_name in nodes_by_id:
            raise ValueError(f"Node {node_name} appears more than once.")
        node_type = node.get("type")
        if node_type not in node_types:
            raise ValueError(f"Node {node_name} uses an unknown type: {node_type!r}.")
        nodes_by_id[node_name] = node

    for index, edge in enumerate(edges, start=1):
        edge_name = edge.get("id") if isinstance(edge, dict) else None
        display_id = edge_name if isinstance(edge_name, str) else f"number {index}"
        if not isinstance(edge, dict):
            raise ValueError(f"Edge {display_id} must be an object.")
        source_id = edge.get("source")
        target_id = edge.get("target")
        if source_id not in nodes_by_id:
            raise ValueError(f"Edge {display_id} starts at missing node {source_id!r}.")
        if target_id not in nodes_by_id:
            raise ValueError(f"Edge {display_id} points to missing node {target_id!r}.")

        label = edge.get("label", "")
        if not isinstance(label, str):
            raise ValueError(f"Edge {display_id} has a label that must be text.")
        if not label:
            continue

        source_node = nodes_by_id[source_id]
        definition = node_types[source_node["type"]]
        allowed = definition.get("branches")
        if definition.get("branches_from") == "options":
            config = source_node.get("config", {})
            options_field = next(
                (field for field in definition.get("fields", []) if field.get("key") == "options"),
                {},
            )
            options = config.get("options", options_field.get("default", "")) if isinstance(config, dict) else options_field.get("default", "")
            allowed = [option.strip() for option in options.split(",") if option.strip()] if isinstance(options, str) else []
        if allowed is not None and label.casefold() not in {item.casefold() for item in allowed}:
            choices = ", ".join(allowed)
            raise ValueError(f"Edge {display_id} has label {label!r}, which is not allowed from node {source_id}. Use: {choices}.")
