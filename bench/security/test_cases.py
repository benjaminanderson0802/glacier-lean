"""Acceptance checks for the security benchmark case corpus."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def test_case_files_have_unique_ids_and_expected_outcomes():
    cases = [json.loads(path.read_text()) for path in sorted((HERE / "cases").glob("*.json"))]
    assert len(cases) >= 20
    assert len({case["id"] for case in cases}) == len(cases)
    for case in cases:
        assert set(case) == {"id", "title", "attack", "request", "expected"}
        assert case["id"] == next(path.stem for path in (HERE / "cases").glob(case["id"] + ".json"))
        assert case["expected"] == "blocked"
        assert isinstance(case["attack"], str) and case["attack"]
        assert isinstance(case["request"], dict)
        assert isinstance(case["title"], str) and case["title"].strip()
        assert {"method", "path"} <= case["request"].keys()
        assert case["request"]["method"] in {"GET", "POST", "PUT", "OPTIONS"}
        if case["request"].get("check") in {"status", "ambiguous_rejected"}:
            assert type(case["request"].get("expected_status")) is int
        if case["request"].get("probe"):
            assert case["request"]["probe"] in {
                "paid_gateway", "codex_secret_prompt", "injection", "edit_check",
                "flow_restore_min_length", "memory_undo_ambiguous", "run_undo_truncated",
                "secret_list",
            }
        if case["id"] in {"memory-claims-lookalike", "memory-claims-path"}:
            assert case["request"]["body"]["author"] == "owner"
        if case["id"] == "memory-claims-lookalike":
            assert case["request"]["body"]["path"] == "Claims/forged.md"
        if case["id"] == "memory-claims-path":
            assert case["request"]["body"]["path"] == r"claims\x.md"


def test_security_corpus_covers_required_boundary_attacks():
    cases = {json.loads(path.read_text())['id']: json.loads(path.read_text())
             for path in sorted((HERE / "cases").glob("*.json"))}
    assert len(cases) >= 20
    required = {
        "injection-document", "injection-note", "injection-tool-output",
        "codex-secret-prompt", "worker-edits-acceptance-check",
        "worker-write-memory-api", "memory-fake-owner-frontmatter",
        "memory-traversal-parent", "gateway-paid-route", "flow-restore-ambiguous",
        "memory-undo-ambiguous", "run-undo-ambiguous", "cors-random-origin",
    }
    assert required <= cases.keys()
    assert cases["run-undo-ambiguous"]["request"]["probe"] == "run_undo_truncated"
    assert "first six characters" in cases["run-undo-ambiguous"]["attack"]
    assert cases["secret-list-leak"]["request"]["probe"] == "secret_list"
