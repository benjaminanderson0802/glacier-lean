import csv
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import bid_triage  # noqa: E402


def test_fixture_filters_by_trade_and_counties_and_keeps_source_links():
    notices = bid_triage.read_notices(ROOT / "tests/fixtures/notices.csv")

    result = bid_triage.build_digest(
        notices,
        trade="electrical",
        counties={"mobile", "baldwin"},
        as_of="2026-10-10",
    )

    assert [row["notice_number"] for row in result["matches"]] == ["PW-2026-017"]
    assert result["matches"][0]["county"] == "Mobile"
    assert result["matches"][0]["bid_date"] == "2026-11-05T10:00:00-05:00"
    assert "https://bids.oakcreek.example/notices/PW-2026-017" in bid_triage.render_markdown(result)
    assert result["source_mode"] == "user_supplied_fixture"


def test_missing_due_date_is_visible_as_uncertain_not_guessed():
    notice = {
        "notice_number": "PW-MISSING-DUE",
        "project": "Electrical service replacement",
        "advertising_agency": "Town of Oak Creek",
        "county": "Mobile",
        "municipality": "Oak Creek",
        "bid_date": "",
        "prebid_meeting": "",
        "description": "Replace electrical service equipment",
        "official_url": "https://bids.oakcreek.example/notices/PW-MISSING-DUE",
        "source_mode": "forwarded_official_notice",
        "received_at": "2026-10-10",
    }

    result = bid_triage.build_digest([notice], "electrical", {"mobile"}, "2026-10-10")
    rendered = bid_triage.render_markdown(result)

    assert len(result["matches"]) == 1
    assert result["matches"][0]["deadline_status"] == "uncertain — check controlling notice"
    assert "uncertain — check controlling notice" in rendered


def test_input_rejects_non_official_or_non_https_source_urls(tmp_path):
    source = tmp_path / "notices.csv"
    with source.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=bid_triage.REQUIRED_FIELDS)
        writer.writeheader()
        writer.writerow({
            "notice_number": "PW-1", "project": "Electrical upgrade",
            "advertising_agency": "Town", "county": "Mobile", "municipality": "Town",
            "bid_date": "2026-11-05", "prebid_meeting": "", "description": "Electrical",
            "official_url": "http://not-an-official-source.invalid/", "source_mode": "browser_scrape",
            "received_at": "2026-10-10",
        })

    with pytest.raises(ValueError, match="https URL"):
        bid_triage.read_notices(source)


def test_manifest_matches_shared_venture_schema():
    import jsonschema

    schema = json.loads((ROOT.parent / "venture.schema.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "venture.json").read_text(encoding="utf-8"))

    jsonschema.validate(manifest, schema)
    assert isinstance(manifest["secrets_needed"], list)
