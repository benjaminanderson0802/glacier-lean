"""Checks the prepared, minimal Jobber setup instructions."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_ready_manifest_has_one_bundled_owner_setup_step():
    manifest = json.loads((ROOT / "venture.json").read_text(encoding="utf-8"))

    assert manifest["status"] == "ready"
    assert len(manifest["your_steps"]) == 1
    step = manifest["your_steps"][0]
    assert step["id"] == "jobber-setup"
    assert "OWNER-STEPS.md" in step["detail"]


def test_jobber_custom_field_values_are_prepared_exactly():
    setup = (ROOT / "JOBBER-SETUP.md").read_text(encoding="utf-8")

    for label in ("Equipment Brand", "Equipment Model", "Equipment Serial", "Install Date"):
        assert label in setup
    assert "Text" in setup
    assert "non-transferable" in setup
    assert "leave the default value blank" in setup
    assert "Gear → Settings → Custom Fields → Jobs → Add Field" in setup


def test_owner_steps_do_not_require_term_decisions_or_outreach():
    steps = (ROOT / "OWNER-STEPS.md").read_text(encoding="utf-8").casefold()

    assert "one setup session" in steps
    assert "no portal terms decision" in steps
    assert "no outreach" in steps
    assert "uncertain — please check" in steps
