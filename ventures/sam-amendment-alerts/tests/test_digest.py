import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from digest import build_digest


def load_snapshot(name):
    return json.loads((ROOT / "tests" / "fixtures" / name).read_text())


def test_two_snapshots_find_amendments_deadline_changes_and_new_notices():
    digest = build_digest(
        load_snapshot("snapshot-2026-10-09.json"),
        load_snapshot("snapshot-2026-10-10.json"),
        naics_codes={"423840"},
    )

    assert digest["status"] == "match"
    assert digest["trade"] == "industrial supplies merchant wholesalers"
    assert digest["snapshot_date"] == "2026-10-10"
    assert len(digest["events"]) == 2
    by_notice = {event["solicitation_number"]: event for event in digest["events"]}
    assert by_notice["SPE4A7-26-Q-1234"]["kind"] == "amendment_and_deadline_change"
    assert by_notice["SPE4A7-26-Q-1234"]["previous_deadline"] == "2026-10-22T14:00:00-04:00"
    assert by_notice["SPE4A7-26-Q-1234"]["response_deadline"] == "2026-10-28T14:00:00-04:00"
    assert by_notice["SPE7M1-26-Q-0987"]["kind"] == "new_notice"
    assert all(event["naics_code"] == "423840" for event in digest["events"])


def test_digest_carries_provenance_and_does_not_claim_history_before_first_snapshot():
    digest = build_digest(
        load_snapshot("snapshot-2026-10-09.json"),
        load_snapshot("snapshot-2026-10-10.json"),
        naics_codes={"423840"},
    )

    assert digest["source_url"] == "https://api.sam.gov/opportunities/v2/search"
    assert digest["coverage_note"] == (
        "Changes are observed only between these saved snapshots; this does not reconstruct "
        "amendments published before the first snapshot. Verify each notice on SAM.gov."
    )
    assert digest["retrieved_at"] == "2026-10-10T12:00:00Z"


def test_digest_reports_no_match_with_the_source_date():
    # SAM.gov v2 response envelope fields are documented by GSA:
    # https://open.gsa.gov/api/get-opportunities-public-api/
    # The response has no records, and its sole empty page covers that total.
    before = {
        "retrieved_at": "2026-10-09T12:00:00Z",
        "source_url": "https://api.sam.gov/opportunities/v2/search?ncode=423840",
        "totalRecords": 0,
        "limit": 1000,
        "offset": 0,
        "opportunitiesData": [],
    }
    after = {
        "retrieved_at": "2026-10-10T12:00:00Z",
        "source_url": "https://api.sam.gov/opportunities/v2/search?ncode=423840",
        "totalRecords": 0,
        "limit": 1000,
        "offset": 0,
        "opportunitiesData": [],
    }

    digest = build_digest(before, after, naics_codes={"423840"})

    assert digest["status"] == "no match found in SAM.gov as of 2026-10-10"
    assert digest["events"] == []


def test_fixture_snapshots_match_the_documented_opportunities_v2_envelope():
    snapshot = load_snapshot("snapshot-2026-10-10.json")

    assert set(snapshot) >= {"opportunitiesData", "totalRecords", "limit", "offset"}
    notice = snapshot["opportunitiesData"][0]
    assert set(notice) >= {"noticeId", "title", "naicsCode", "responseDeadLine", "modifiedDate"}
    assert notice["typeOfSetAsideDescription"] == "Small Business Set-Aside (FAR 19.5)"
