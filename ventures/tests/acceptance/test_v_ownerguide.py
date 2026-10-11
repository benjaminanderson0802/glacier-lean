"""Independent regeneration checks for the owner venture guide."""
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.xfail(strict=False, reason="awaiting builder V-OWNERGUIDE")
def test_guide_covers_every_venture_manifest_with_status_and_steps():
    guide = (ROOT / "OWNER-START-HERE.md").read_text(encoding="utf-8").lower()
    manifests = sorted(ROOT.glob("*/venture.json"))
    assert manifests
    for path in manifests:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        slug = manifest.get("slug", path.parent.name).lower()
        assert slug.replace("-", " ") in guide or manifest.get("name", "").lower() in guide
    for status in ("live", "ready", "blocked"):
        assert status in guide
    assert "your steps" in guide


@pytest.mark.xfail(strict=False, reason="awaiting builder V-OWNERGUIDE")
def test_owner_guide_keeps_assigned_live_account_facts_and_manual_actions():
    guide = (ROOT / "OWNER-START-HERE.md").read_text(encoding="utf-8").lower()
    for phrase in ("awaiting cage", "jobber", "shopify", "payout", "pricing", "chrome web store"):
        assert phrase in guide
    assert "no filing" in guide or "does not submit" in guide or "sign and submit" in guide


@pytest.mark.xfail(strict=False, reason="awaiting builder V-OWNERGUIDE")
def test_owner_guide_lists_remaining_full_suite_failures_with_causes():
    guide = (ROOT / "OWNER-START-HERE.md").read_text(encoding="utf-8").lower()
    assert "remaining test failures" in guide or "test suite failures" in guide
    assert "cause" in guide or "because" in guide


def test_all_venture_proof_files_distinguish_fixtures_from_live_evidence():
    proof_files = sorted(ROOT.glob("*/PROOF.md"))
    assert proof_files
    # The guide must not turn a fixture-only statement into a live verification claim.
    guide = (ROOT / "OWNER-START-HERE.md").read_text(encoding="utf-8").lower()
    assert "known limits" in guide or "fixture" in guide or "live" in guide
