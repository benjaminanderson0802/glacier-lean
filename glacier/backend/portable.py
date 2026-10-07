"""Portable, validated JSON export and import for Glacier flows."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


_NODE_TYPES_PATH = Path(__file__).resolve().parents[1] / "contract" / "node_types.json"


def export_flow(flow: dict) -> str:
    """Return a readable, versioned JSON file containing a flow."""
    package = {
        "glacier_flow": 1,
        "exported_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "flow": flow,
    }
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
            options = config.get("options", "") if isinstance(config, dict) else ""
            allowed = [option.strip() for option in options.split(",") if option.strip()] if isinstance(options, str) else []
        if allowed is not None and label.casefold() not in {item.casefold() for item in allowed}:
            choices = ", ".join(allowed)
            raise ValueError(f"Edge {display_id} has label {label!r}, which is not allowed from node {source_id}. Use: {choices}.")
