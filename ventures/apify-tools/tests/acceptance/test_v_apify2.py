"""Independent acceptance checks for the second state contractor Actor."""
import os
from pathlib import Path

import pytest

VENTURES = Path(__file__).resolve().parents[3]


def test_second_board_has_separate_deployable_actor_using_shared_runner():
    candidates = [p for p in VENTURES.glob("apify-tools-*") if p.is_dir() and p.name != "apify-tools"]
    assert candidates, "second state board Actor folder is missing"
    actor = candidates[0]
    assert (actor / ".actor/input_schema.json").is_file()
    assert (actor / "requirements.txt").is_file()
    assert (actor / "src/actor_template.py").is_file() or (actor / "src/main.py").is_file()
    assert (actor / "README.md").is_file()


def test_second_board_has_explicit_owner_publication_steps_and_evidence():
    candidates = [p for p in VENTURES.glob("apify-tools-*") if p.is_dir() and p.name != "apify-tools"]
    assert candidates
    actor = candidates[0]
    readme = (actor / "README.md").read_text(encoding="utf-8").lower()
    proof = (actor / "PROOF.md").read_text(encoding="utf-8").lower()
    assert "your step" in readme or "owner step" in readme
    assert "live" in proof and ("fixture" in proof or "canary" in proof)
    assert not any(word in readme for word in ("automatically submits", "automatically publishes"))


@pytest.mark.skipif(os.getenv("APIFY2_LIVE") != "1", reason="set APIFY2_LIVE=1 only for the public board canary")
def test_second_board_live_canary_has_a_source_link():
    candidates = [p for p in VENTURES.glob("apify-tools-*") if p.is_dir() and p.name != "apify-tools"]
    assert candidates
    proof = (candidates[0] / "PROOF.md").read_text(encoding="utf-8")
    assert "https://" in proof and "canary" in proof.lower()
