"""Revision-retention checks for the superseded B-BID-REVISIONS card."""
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT / "scripts"))

import bid_triage  # noqa: E402


def notice(**changes):
    row = {
        "notice_number": "BID-42",
        "project": "Public works building construction",
        "advertising_agency": "Mobile Public Works",
        "county": "Mobile",
        "municipality": "Mobile",
        "bid_date": "2026-10-21",
        "prebid_meeting": "",
        "description": "General contractor building construction",
        "official_url": "https://alabamabuilds.gov/AdvertisementBids/42",
        "source_mode": "forwarded_official_notice",
        "received_at": "2026-10-10T10:00:00-05:00",
    }
    return {**row, **changes}


def digest(rows):
    return bid_triage.build_digest(rows, "general-contracting", {"Mobile"}, "2026-10-10")


def test_later_revision_wins_independent_of_input_order_and_keeps_prior_deadline():
    earlier = notice()
    later = notice(bid_date="2026-11-02", received_at="2026-10-11T10:00:00-05:00")

    for rows in ([earlier, later], [later, earlier]):
        result = digest(rows)
        assert len(result["matches"]) == 1
        item = result["matches"][0]
        rendered = bid_triage.render_markdown(result)
        assert item["bid_date"] == "2026-11-02"
        assert item["revision_conflict"] is False
        assert "Earlier supplied version: bid due 2026-10-21" in rendered
        assert "issuing authority's notice" in rendered


def test_same_notice_number_from_different_issuers_is_not_collapsed():
    first = notice(advertising_agency="Mobile Public Works")
    second = notice(advertising_agency="Baldwin County Works", county="Baldwin")
    result = bid_triage.build_digest([first, second], "general-contracting", {"Mobile", "Baldwin"}, "2026-10-10")
    assert {item["advertising_agency"] for item in result["matches"]} == {
        "Mobile Public Works", "Baldwin County Works"
    }


def test_equal_or_missing_revision_provenance_keeps_conflicting_dates_uncertain():
    first = notice()
    second = notice(bid_date="2026-10-30")
    result = digest([first, second])
    rendered = bid_triage.render_markdown(result)
    assert "uncertain - please check" in rendered
    assert "2026-10-21" in rendered and "2026-10-30" in rendered
    assert result["matches"][0]["revision_conflict"] is True

    second["received_at"] = ""
    result = digest([first, second])
    assert result["matches"][0]["revision_conflict"] is True


def test_missing_notice_facts_are_called_uncertain_in_rendered_digest():
    result = digest([notice(advertising_agency="", bid_date="", prebid_meeting="")])
    rendered = bid_triage.render_markdown(result)
    assert rendered.count("uncertain - please check") >= 3

