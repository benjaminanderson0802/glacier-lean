"""Integrity regressions for B-SAM-INTEGRITY, separate from independent acceptance checks."""
import importlib.util
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("sam_digest_integrity", KIT / "scripts/digest.py")
digest_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(digest_module)


def complete_snapshot(retrieved_at, rows, *, scope=("423840",)):
    return {
        "opportunitiesData": rows,
        "totalRecords": len(rows),
        "limit": 100,
        "offset": 0,
        "retrieved_at": retrieved_at,
        "source_url": "https://api.sam.gov/opportunities/v2/search",
        "naics_codes": list(scope),
    }


def test_rejects_reversed_snapshot_dates():
    before = complete_snapshot("2026-10-11T00:00:00Z", [])
    after = complete_snapshot("2026-10-10T00:00:00Z", [])

    with pytest.raises(ValueError, match="chronological"):
        digest_module.build_digest(before, after, naics_codes={"423840"})


def test_rejects_different_recorded_collection_scopes():
    before = complete_snapshot("2026-10-09T00:00:00Z", [], scope=("423840",))
    after = complete_snapshot("2026-10-10T00:00:00Z", [], scope=("423830",))

    with pytest.raises(ValueError, match="scope"):
        digest_module.build_digest(before, after, naics_codes={"423840"})


def test_identical_complete_snapshots_are_a_dated_no_match():
    before = complete_snapshot("2026-10-09T00:00:00Z", [])
    after = complete_snapshot("2026-10-10T00:00:00Z", [])

    result = digest_module.build_digest(before, after, naics_codes={"423840"})

    assert result["status"] == "no match found in SAM.gov as of 2026-10-10"
    assert result["events"] == []
