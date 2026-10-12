"""Acceptance check for the reusable local data pipeline example."""

import json
from pathlib import Path


def test_local_data_pipeline_template_uses_only_supported_nodes_and_links_them():
    path = Path(__file__).resolve().parents[3] / "templates" / "tpl-local-data-pipeline.json"
    flow = json.loads(path.read_text(encoding="utf-8"))
    assert flow["id"] == "tpl-local-data-pipeline"
    nodes = {node["id"]: node for node in flow["nodes"]}
    assert {node["type"] for node in nodes.values()} >= {
        "data_table", "json_transform", "csv_file", "delay", "structured_ai", "email_send"
    }
    assert all(edge["source"] in nodes and edge["target"] in nodes for edge in flow["edges"])
    assert any(edge["source"] == "table" and edge["target"] == "json" for edge in flow["edges"])
    manifest = json.loads((path.parent / "manifest" / "MANIFEST.json").read_text(encoding="utf-8"))
    assert any(entry["id"] == flow["id"] and entry["file"] == path.name for entry in manifest["templates"])


def test_email_trigger_template_saves_each_message_to_local_memory():
    root = Path(__file__).resolve().parents[3] / "templates"
    flow = json.loads((root / "tpl-email-inbox-note.json").read_text(encoding="utf-8"))
    nodes = {node["id"]: node for node in flow["nodes"]}
    assert nodes["email"]["type"] == "email_trigger"
    assert nodes["save"]["type"] == "note"
    assert any(edge["source"] == "email" and edge["target"] == "save" for edge in flow["edges"])
    manifest = json.loads((root / "manifest" / "MANIFEST.json").read_text(encoding="utf-8"))
    assert any(entry["id"] == flow["id"] and entry["file"] == "tpl-email-inbox-note.json" for entry in manifest["templates"])


def test_email_search_template_uses_read_only_mail_step():
    root = Path(__file__).resolve().parents[3] / "templates"
    flow = json.loads((root / "tpl-email-search-note.json").read_text(encoding="utf-8"))
    nodes = {node["id"]: node for node in flow["nodes"]}
    assert nodes["search"]["type"] == "email_read"
    assert nodes["save"]["type"] == "note"
    assert any(edge["source"] == "search" and edge["target"] == "save" for edge in flow["edges"])
    manifest = json.loads((root / "manifest" / "MANIFEST.json").read_text(encoding="utf-8"))
    assert any(entry["id"] == flow["id"] and entry["file"] == "tpl-email-search-note.json" for entry in manifest["templates"])


def test_item_processor_template_loops_back_and_is_gallery_registered():
    root = Path(__file__).resolve().parents[3] / "templates"
    flow = json.loads((root / "tpl-item-processor.json").read_text(encoding="utf-8"))
    nodes = {node["id"]: node for node in flow["nodes"]}
    assert nodes["each"]["type"] == "for_each"
    assert any(edge["source"] == "each" and edge["label"] == "each" for edge in flow["edges"])
    assert any(edge["source"] == "save" and edge["target"] == "each" for edge in flow["edges"])
    manifest = json.loads((root / "manifest" / "MANIFEST.json").read_text(encoding="utf-8"))
    assert any(entry["id"] == flow["id"] and entry["file"] == "tpl-item-processor.json" for entry in manifest["templates"])
