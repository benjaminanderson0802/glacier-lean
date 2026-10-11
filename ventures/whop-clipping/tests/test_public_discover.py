import json
from pathlib import Path
import time

from scripts.public_discover import PublicDiscoverScout, parse_campaign_cards, parse_campaign_detail
from scripts.interfaces import Campaign
from scripts.producer import produce_ready
from scripts.distributor import status_report
from scripts.ledger import Ledger


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
    assert [item.id for item in scout.list_campaigns()] == [campaign_id]
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
    assert scout.list_campaigns()[0].id == campaign_id
    (tmp_path / "joined_campaigns.txt").write_text(campaign_id + "\n", encoding="utf-8")
    scout = PublicDiscoverScout({"clip_home": str(tmp_path)}, fetcher=fetch, clock=lambda: 1000.0)
    assert scout.list_campaigns()[0].id == campaign_id


def test_public_scout_returns_campaign_contract_objects(tmp_path):
    fixture_dir = FIXTURES / "contentrewards"
    campaign_id = "188c3e39-7850-4896-94df-e7a5be0cfec3"

    def fetch(url):
        if url.endswith("/discover"):
            return (fixture_dir / "discover.html").read_text(encoding="utf-8")
        return (fixture_dir / f"{campaign_id}.html").read_text(encoding="utf-8")

    (tmp_path / "joined_campaigns.txt").write_text(campaign_id + "\n", encoding="utf-8")
    scout = PublicDiscoverScout({"clip_home": str(tmp_path)}, fetcher=fetch, clock=lambda: 1000.0)
    campaigns = scout.list_campaigns()

    assert len(campaigns) == 1
    assert isinstance(campaigns[0], Campaign)
    assert campaigns[0].id == campaign_id
    assert set(campaigns[0].platforms) == {"instagram", "tiktok", "x", "youtube"}


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
    assert [item.id for item in joined] == ["camp-joined"]
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


def test_producer_normalizes_campaign_dicts_from_legacy_scouts(tmp_path):
    class DictScout:
        def list_campaigns(self):
            return [{
                "id": "dict-campaign", "name": "Dictionary campaign",
                "url": "https://contentrewards.com/c/campaigns/dict-campaign",
                "cpm_usd": 1.5, "budget_left_usd": 50,
                "platforms": ["youtube"], "rules_text": "Minimum length: 20 seconds.",
                "source_links": [],
            }]

    result = produce_ready({"approved_campaign_ids": ["dict-campaign"], "channels": ["@first"]},
                           home=tmp_path, scout=DictScout(), campaign_clips={"dict-campaign": []},
                           target_stock=0)

    assert result["campaigns"] == 1
    assert result["error_count"] == 0


def test_discovery_failure_is_logged_and_counted(tmp_path):
    class BrokenScout:
        def list_campaigns(self):
            raise OSError("public discover is unavailable")

    result = produce_ready({}, home=tmp_path, scout=BrokenScout(), target_stock=0)

    assert result["campaigns"] == 0
    assert result["error_count"] == 1
    assert result["failure_count"] == 1
    assert result["errors"][0]["kind"] == "campaign_discovery_failed"
    assert any(event["kind"] == "producer_error" for event in Ledger(tmp_path).events())


def test_producer_cli_returns_nonzero_and_prints_failure_counts(tmp_path, monkeypatch, capsys):
    import scripts.producer as producer_module

    class BrokenScout:
        def list_campaigns(self):
            raise OSError("discover unavailable")

    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(producer_module, "load_plugin", lambda *_args, **_kwargs: BrokenScout())

    status = producer_module.main([
        "--config", str(config_path), "--home", str(tmp_path), "--target-stock", "0",
    ])

    output = json.loads(capsys.readouterr().out)
    assert status == 1
    assert output["error_count"] == 1
    assert output["failure_count"] == 1


def test_join_suggestions_rank_unjoined_youtube_campaigns_with_budget(tmp_path):
    scout = PublicDiscoverScout({"clip_home": str(tmp_path)}, fetcher=lambda _url: "", clock=lambda: 1000.0)
    scout._cards = [
        {"id": "joined", "name": "Joined", "url": "https://contentrewards.com/c/campaigns/joined",
         "cpm_usd": 12, "budget_left_usd": 100, "platforms": ["youtube"], "rules_text": ""},
        {"id": "best", "name": "Best", "url": "https://contentrewards.com/c/campaigns/best",
         "cpm_usd": 8, "budget_left_usd": 300, "platforms": ["youtube_shorts"], "rules_text": ""},
        {"id": "no-budget", "name": "No budget", "url": "https://contentrewards.com/c/campaigns/no-budget",
         "cpm_usd": 99, "budget_left_usd": 0, "platforms": ["youtube"], "rules_text": ""},
        {"id": "other-platform", "name": "Other platform", "url": "https://contentrewards.com/c/campaigns/other",
         "cpm_usd": 50, "budget_left_usd": 100, "platforms": ["tiktok"], "rules_text": ""},
        {"id": "rules-prohibited", "name": "Rules prohibited", "url": "https://contentrewards.com/c/campaigns/prohibited",
         "cpm_usd": 40, "budget_left_usd": 100, "platforms": ["youtube"], "rules_text": "YouTube is not allowed."},
        {"id": "unknown-budget", "name": "Unknown budget", "url": "https://contentrewards.com/c/campaigns/unknown-budget",
         "cpm_usd": 30, "budget_left_usd": None, "platforms": ["youtube"], "rules_text": ""},
        {"id": "second", "name": "Second", "url": "https://contentrewards.com/c/campaigns/second",
         "cpm_usd": 8, "budget_left_usd": 100, "platforms": ["youtube"], "rules_text": ""},
    ]
    scout._by_id = {row["id"]: row for row in scout._cards}
    (tmp_path / "joined_campaigns.txt").write_text(
        "https://contentrewards.com/c/campaigns/joined\n", encoding="utf-8"
    )
    scout._detail = lambda card: card

    suggestions = scout.join_suggestions(limit=10)

    assert [item["id"] for item in suggestions] == ["best", "second"]
    assert json.loads((tmp_path / "join_suggestions.json").read_text(encoding="utf-8"))["campaigns"] == suggestions


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
