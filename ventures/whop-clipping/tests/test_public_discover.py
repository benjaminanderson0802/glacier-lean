import json
from pathlib import Path
import time

from scripts.public_discover import PublicDiscoverScout, parse_campaign_cards, parse_campaign_detail
from scripts.producer import produce_ready
from scripts.distributor import status_report


FIXTURES = Path(__file__).parent / "fixtures"


def test_parser_reads_discover_cards_and_detail_fields():
    cards = parse_campaign_cards((FIXTURES / "discover.html").read_text(encoding="utf-8"))
    assert len(cards) == 2
    assert cards[0]["name"] == "Launch highlights"
    assert cards[0]["url"].endswith("/c/campaigns/camp-joined")
    assert cards[0]["cpm_usd"] == 4.5
    assert cards[0]["budget_used_usd"] == 125
    assert cards[0]["budget_total_usd"] == 500
    assert cards[0]["platforms"] == ["youtube", "tiktok"]

    campaign = parse_campaign_detail((FIXTURES / "campaign.html").read_text(encoding="utf-8"), cards[0])
    assert "YouTube Shorts only" in campaign["rules_text"]
    assert "Minimum length: 20 seconds." in campaign["rules_text"]
    assert campaign["source_links"] == [
        {"url": "https://media.example.test/launch.mp4", "label": "Approved footage"}
    ]


def test_parser_reads_public_content_rewards_server_rendered_fixtures():
    cards = parse_campaign_cards((FIXTURES / "discover_page.html").read_text(encoding="utf-8"))
    campaign = next(item for item in cards if item["id"] == "61dcced7-34d2-4dc4-ac6c-5bf6bae5b8e7")
    assert campaign["name"] == 'Audien & LUKE ALEXANDER "7 Miles High"'
    assert campaign["cpm_usd"] == 1
    assert campaign["budget_used_usd"] == 36.56
    assert campaign["budget_total_usd"] == 1250
    assert campaign["platforms"] == ["instagram", "tiktok"]

    detail = parse_campaign_detail((FIXTURES / "campaign_detail_page.html").read_text(encoding="utf-8"), campaign)
    assert detail["budget_used_usd"] == 36.56
    assert detail["budget_total_usd"] == 1250
    assert {"instagram", "tiktok"}.issubset(detail["platforms"])
    assert "Dropbox" in detail["rules_text"]
    assert isinstance(detail["source_links"], list)


def test_parser_reads_live_discover_anchor_cards_and_compact_amounts():
    live_fixtures = FIXTURES / "contentrewards"
    cards = parse_campaign_cards((live_fixtures / "discover.html").read_text(encoding="utf-8"))
    assert len(cards) > 0

    boxabl = next(item for item in cards if item["name"] == "Boxabl Official Clipping")
    assert boxabl["id"] == "188c3e39-7850-4896-94df-e7a5be0cfec3"
    assert boxabl["cpm_usd"] == 0.50
    assert boxabl["budget_used_usd"] == 20100
    assert boxabl["budget_total_usd"] == 85000

    detail = parse_campaign_detail(
        (live_fixtures / f"{boxabl['id']}.html").read_text(encoding="utf-8"), boxabl
    )
    assert {"youtube", "tiktok", "instagram", "x"}.issubset(detail["platforms"])
    assert "pre-approved YouTube videos" in detail["rules_text"]
    assert isinstance(detail["source_links"], list)


def test_joined_campaigns_match_uuid_across_hosts_and_bare_ids(tmp_path):
    fixture_dir = FIXTURES / "contentrewards"
    campaign_id = "188c3e39-7850-4896-94df-e7a5be0cfec3"
    fetches = []

    def fetch(url):
        fetches.append(url)
        if url.endswith("/discover"):
            return (fixture_dir / "discover.html").read_text(encoding="utf-8")
        return (fixture_dir / f"{campaign_id}.html").read_text(encoding="utf-8")

    (tmp_path / "joined_campaigns.txt").write_text(
        f"{campaign_id}\nhttps://whop.com/c/campaigns/{campaign_id}\n", encoding="utf-8"
    )
    scout = PublicDiscoverScout({"clip_home": str(tmp_path)}, fetcher=fetch, clock=lambda: 1000.0)
    assert [item["id"] for item in scout.list_campaigns()] == [campaign_id]
    assert fetches.count("https://contentrewards.com/c/campaigns/" + campaign_id) == 1


def test_joined_campaigns_match_contentrewards_url_and_bare_uuid(tmp_path):
    fixture_dir = FIXTURES / "contentrewards"
    campaign_id = "188c3e39-7850-4896-94df-e7a5be0cfec3"

    def fetch(url):
        if url.endswith("/discover"):
            return (fixture_dir / "discover.html").read_text(encoding="utf-8")
        return (fixture_dir / f"{campaign_id}.html").read_text(encoding="utf-8")

    (tmp_path / "joined_campaigns.txt").write_text(
        f"https://contentrewards.com/c/campaigns/{campaign_id}\n", encoding="utf-8"
    )
    scout = PublicDiscoverScout({"clip_home": str(tmp_path)}, fetcher=fetch, clock=lambda: 1000.0)
    assert scout.list_campaigns()[0]["id"] == campaign_id
    (tmp_path / "joined_campaigns.txt").write_text(campaign_id + "\n", encoding="utf-8")
    scout = PublicDiscoverScout({"clip_home": str(tmp_path)}, fetcher=fetch, clock=lambda: 1000.0)
    assert scout.list_campaigns()[0]["id"] == campaign_id


def test_scout_only_lists_joined_urls_and_surfaces_suggestions(tmp_path):
    now = [1000.0]
    calls = []

    def fetch(url):
        calls.append(url)
        if url.endswith("/discover"):
            return (FIXTURES / "discover.html").read_text(encoding="utf-8")
        return (FIXTURES / "campaign.html").read_text(encoding="utf-8")

    (tmp_path / "joined_campaigns.txt").write_text(
        "https://contentrewards.com/c/campaigns/camp-joined\n", encoding="utf-8"
    )
    scout = PublicDiscoverScout({"clip_home": str(tmp_path)}, fetcher=fetch,
                                clock=lambda: now[0])
    joined = scout.list_campaigns()
    assert [item["id"] for item in joined] == ["camp-joined"]
    assert [item["url"] for item in scout.join_suggestions()] == [
        "https://contentrewards.com/c/campaigns/camp-suggested"
    ]
    assert scout.list_campaigns() == joined
    assert calls.count("https://contentrewards.com/c/discover") == 1

    cached = PublicDiscoverScout({"clip_home": str(tmp_path)}, fetcher=fetch,
                                 clock=lambda: now[0] + 1800)
    cached._discover_cards()
    assert calls.count("https://contentrewards.com/c/discover") == 1
    expired = PublicDiscoverScout({"clip_home": str(tmp_path)}, fetcher=fetch,
                                  clock=lambda: now[0] + 3601)
    expired._discover_cards()
    assert calls.count("https://contentrewards.com/c/discover") == 2


def test_producer_accepts_joined_campaign_without_campaign_id_config(tmp_path):
    def fetch(url):
        if url.endswith("/discover"):
            return (FIXTURES / "discover.html").read_text(encoding="utf-8")
        detail = (FIXTURES / "campaign.html").read_text(encoding="utf-8")
        return detail.replace("camp-joined", "camp-suggested") if "camp-suggested" in url else detail

    (tmp_path / "joined_campaigns.txt").write_text(
        "https://contentrewards.com/c/campaigns/camp-joined\n", encoding="utf-8"
    )
    scout = PublicDiscoverScout({"clip_home": str(tmp_path)}, fetcher=fetch, clock=lambda: 1000.0)
    result = produce_ready({"approved_campaign_ids": [], "channels": ["@first"], "live": False},
                           home=tmp_path, scout=scout, campaign_clips={"camp-joined": []},
                           target_stock=0)
    assert result["campaigns"] == 1
    assert [item["id"] for item in result["join_suggestions"]] == ["camp-suggested"]


def test_status_report_includes_saved_join_suggestions(tmp_path):
    suggestion = {"id": "camp-suggested", "name": "Creator story", "url": "https://contentrewards.com/c/campaigns/camp-suggested",
                  "cpm_usd": 8, "budget_left_usd": 950}
    (tmp_path / "join_suggestions.json").write_text(
        json.dumps({"updated_at": time.time(), "campaigns": [suggestion]}), encoding="utf-8"
    )
    report = status_report({"channels": []}, home=tmp_path)
    assert report["join_suggestions"] == [suggestion]


def test_public_fetch_uses_identifying_user_agent_and_rejects_api_urls(tmp_path):
    scout = PublicDiscoverScout({"clip_home": str(tmp_path)})
    assert "Glacier" in scout.user_agent and "ben@andersoneducation.us" in scout.user_agent
    try:
        scout._validate_url("https://contentrewards.com/api/campaigns")
    except ValueError as exc:
        assert "robots.txt" in str(exc)
    else:
        raise AssertionError("/api/ URLs must never be fetched")
