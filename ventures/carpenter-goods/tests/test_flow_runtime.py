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


def test_commission_flow_requires_owner_settlement_review_before_amount_is_verified():
    flow_path = Path(__file__).parents[1] / "flows" / "carpenter-track-commissions.json"
    flow = json.loads(flow_path.read_text(encoding="utf-8"))

    assert len(flow["acceptance"]) == 1
    assert flow["acceptance"][0]["kind"] == "human"
    question = flow["acceptance"][0]["question"].casefold()
    assert "signed agreement" in question
    assert "settlement records" in question
    assert "do not approve an amount for payment" in question
    assert "does not authorize glacier to invoice, send, charge, or transfer money" in question
