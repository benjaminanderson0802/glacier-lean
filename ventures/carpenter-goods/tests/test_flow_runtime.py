"""Regression checks for the flow's approval branch wiring."""
import json
from pathlib import Path


def test_owner_input_approval_yes_edge_runs_listing_command():
    flow_path = Path(__file__).parents[1] / "flows" / "carpenter-prepare-listing.json"
    flow = json.loads(flow_path.read_text(encoding="utf-8"))

    edge = next(
        edge for edge in flow["edges"]
        if edge["source"] == "owner_input_ready" and edge["target"] == "prepare_draft"
    )

    assert edge.get("label", "").strip().lower() == "yes"
