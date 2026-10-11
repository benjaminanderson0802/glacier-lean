"""Independent sample audit for C-ALBID-PILOT-TESTER.

Frozen values below come from the customer-transcribed synthetic fixture, not
from an Alabama Builds data export. The official listing itself is checked
separately by the pre-existing read-only listing canary.
"""

import csv
import importlib.util
import sys
from pathlib import Path

import pytest


KIT = Path(__file__).resolve().parents[2]
ROOT = KIT.parents[1]
sys.path.insert(0, str(ROOT))

_SPEC = importlib.util.spec_from_file_location(
    "C_al_bid_pilot_under_test", KIT / "scripts" / "bid_triage.py"
)
assert _SPEC and _SPEC.loader
triage = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(triage)

SAMPLE = KIT / "tests" / "fixtures" / "sample-general-contracting.csv"
AS_OF = "2026-10-10"

# Independent expectations frozen from the supplied sample rows before running
# the unchanged generator. Values are local customer mappings, not official
# Alabama Builds structured fields.
FROZEN_SOURCE_FACTS = {
    "PW-2026-031": {
        "issuer": "Oak Creek Public Works Board",
        "deadline": "2026-11-18T10:00:00-06:00",
        "source": "https://notices.oakcreek.example/public-works/PW-2026-031",
    },
    "PW-2026-032": {
        "issuer": "Baldwin County Commission",
        "deadline": "2026-12-03T14:00:00-06:00",
        "source": "https://notices.baldwincounty.example/bids/PW-2026-032",
    },
    "PW-2026-033": {
        "issuer": "Oak Creek Public Works Board",
        "deadline": "2026-11-25T10:00:00-06:00",
        "source": "https://notices.oakcreek.example/public-works/PW-2026-033",
    },
}


def sample_rows():
    with SAMPLE.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def normalized(text):
    return text.lower().replace("—", "-").replace("–", "-")


def render(rows):
    result = triage.build_digest(
        rows, "general-contracting", {"Mobile", "Baldwin"}, AS_OF
    )
    return result, triage.render_markdown(result)


def test_sample_rows_keep_their_frozen_issuer_deadline_and_source():
    rows = sample_rows()

    # First verify the fixture itself against the independent frozen record.
    assert {row["notice_number"] for row in rows} == set(FROZEN_SOURCE_FACTS)
    for row in rows:
        expected = FROZEN_SOURCE_FACTS[row["notice_number"]]
        assert row["advertising_agency"] == expected["issuer"]
        assert row["bid_date"] == expected["deadline"]
        assert row["official_url"] == expected["source"]
        assert row["official_url"].startswith("https://")

    # Then ensure every in-scope sample record retains those facts in output.
    result, markdown = render(triage.read_notices(SAMPLE))
    expected_ids = {"PW-2026-031", "PW-2026-032"}
    assert {item["notice_number"] for item in result["matches"]} == expected_ids
    for notice_id in expected_ids:
        expected = FROZEN_SOURCE_FACTS[notice_id]
        assert expected["issuer"] in markdown
        assert expected["deadline"] in markdown
        assert expected["source"] in markdown
    assert "PW-2026-033" not in markdown  # Roofing is outside this trade filter.


@pytest.mark.parametrize("field", ["advertising_agency", "bid_date", "prebid_meeting"])
def test_missing_notice_facts_render_uncertain_please_check(field):
    row = dict(sample_rows()[0])
    row[field] = ""

    _, markdown = render([row])

    assert "uncertain - please check" in normalized(markdown)


def test_same_notice_id_with_conflicting_deadlines_is_visible_and_uncertain():
    original = dict(sample_rows()[0])
    conflicting = dict(original, bid_date="2026-11-19T10:00:00-06:00")

    result, markdown = render([original, conflicting])

    assert len(result["matches"]) == 1
    assert result["matches"][0]["revision_conflict"] is True
    assert "uncertain - please check" in normalized(markdown)
    assert original["bid_date"] in markdown
    assert conflicting["bid_date"] in markdown
    assert markdown.count(original["notice_number"]) >= 2
