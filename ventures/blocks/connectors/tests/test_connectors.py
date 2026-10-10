from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from ventures.blocks.connectors import ApifyClient, JobberClient, ShipStationClient, ShopifyClient
from ventures.blocks.connectors.common import ConnectorError


FIXTURES = Path(__file__).parent.parent / "fixtures"


def fixture_json(platform: str, name: str):
    return json.loads((FIXTURES / platform / name).read_text(encoding="utf-8"))


def test_jobber_reads_account_and_cursor_pages_from_official_fixtures():
    responses = [fixture_json("jobber", "account.json"), fixture_json("jobber", "jobs_page_1.json"), fixture_json("jobber", "jobs_page_2.json")]
    requests = []

    def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        return httpx.Response(200, json=responses.pop(0))

    client = JobberClient(access_token="fixture-token", transport=httpx.MockTransport(handler), sleep=lambda _: None)
    assert client.test_connection() == {"connected": True, "account": "Fixture HVAC"}
    assert [job["id"] for job in client.get_jobs()] == ["job-1", "job-2"]
    assert requests[-1]["variables"]["after"] == "cursor-1"
    client.close()


def test_shipstation_reads_all_pages_and_uses_api_key_header():
    pages = [fixture_json("shipstation", "shipments_page_1.json"), fixture_json("shipstation", "shipments_page_2.json")]
    seen = []

    def handler(request):
        seen.append((request.url.params["page"], request.headers.get("API-Key")))
        return httpx.Response(200, json=pages.pop(0))

    client = ShipStationClient(api_key="fixture-key", transport=httpx.MockTransport(handler), sleep=lambda _: None)
    assert [row["shipment_id"] for row in client.get_shipments(page_size=1)] == ["se-2102034", "se-2102035"]
    assert seen == [("1", "fixture-key"), ("2", "fixture-key")]
    client.close()


def test_shopify_reads_products_with_cursor_pagination():
    pages = [fixture_json("shopify", "products_page_1.json"), fixture_json("shopify", "products_page_2.json")]
    requests = []

    def handler(request):
        body = json.loads(request.content)
        requests.append(body["variables"]["after"])
        return httpx.Response(200, json=pages.pop(0))

    client = ShopifyClient("fixture-store.myshopify.com", access_token="fixture-token", transport=httpx.MockTransport(handler), sleep=lambda _: None)
    assert [row["id"] for row in client.get_products()] == ["gid://shopify/Product/1", "gid://shopify/Product/2"]
    assert requests == [None, "shopify-cursor-1"]
    client.close()


def test_apify_reads_dataset_items_with_offset_pages():
    pages = [fixture_json("apify", "dataset_items_page_1.json"), fixture_json("apify", "dataset_items_page_2.json")]
    seen = []

    def handler(request):
        seen.append(request.url.params["offset"])
        offset = request.url.params["offset"]
        if offset == "2":
            return httpx.Response(200, json=[], headers={"X-Apify-Pagination-Total": "2"})
        return httpx.Response(200, json=pages.pop(0), headers={"X-Apify-Pagination-Total": "2"})

    client = ApifyClient(api_token="fixture-token", transport=httpx.MockTransport(handler), sleep=lambda _: None)
    assert [row["licenseNumber"] for row in client.get_dataset_items("dataset-1", page_size=1)] == ["LIC-001", "LIC-002"]
    assert seen == ["0", "1"]
    client.close()


def test_apify_connection_check_uses_account_metadata_fixture():
    def handler(request):
        assert request.url.path == "/v2/users/me"
        return httpx.Response(200, json=fixture_json("apify", "user.json"))

    client = ApifyClient(api_token="fixture-token", transport=httpx.MockTransport(handler))
    assert client.test_connection() == {"connected": True, "username": "fixture-owner"}
    client.close()


def test_rate_limit_retries_after_retry_after_header():
    calls = []
    delays = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "2"}, json={"message": "throttled"})
        return httpx.Response(200, json={"data": {"account": {"id": "fixture-account", "name": "Fixture HVAC"}}})

    client = JobberClient(access_token="fixture-token", transport=httpx.MockTransport(handler), sleep=delays.append)
    assert client.test_connection()["connected"] is True
    assert len(calls) == 2
    assert delays == [2.0]
    client.close()


def test_jobber_graphql_throttle_error_retries_with_bounded_delay():
    calls = []
    delays = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(200, json={"errors": [{"message": "Throttled", "extensions": {"code": "THROTTLED"}}]})
        return httpx.Response(200, json={"data": {"account": {"id": "fixture-account", "name": "Fixture HVAC"}}})

    client = JobberClient(access_token="fixture-token", transport=httpx.MockTransport(handler), sleep=delays.append)
    assert client.test_connection()["connected"] is True
    assert len(calls) == 2
    assert delays == [0.5]
    client.close()


def test_shopify_rejects_mutations_by_default():
    client = ShopifyClient("fixture-store.myshopify.com", access_token="fixture-token", transport=httpx.MockTransport(lambda _: pytest.fail("must not send mutation")))
    with pytest.raises(ConnectorError, match="read-only"):
        client.graphql("mutation { productUpdate(product: {}) { product { id } } }")
    client.close()


def test_secret_names_resolve_only_at_request_time_and_missing_secret_is_safe():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"data": {"account": {"id": "fixture-account", "name": "Fixture HVAC"}}})

    client = JobberClient(secret_name="jobber_access_token", secret_resolver=lambda name: "secret-in-keychain", transport=httpx.MockTransport(handler))
    assert client.test_connection()["connected"] is True
    assert requests[0].headers["Authorization"] == "Bearer secret-in-keychain"
    assert "secret-in-keychain" not in repr(client)
    client.close()

    missing = JobberClient(secret_name="absent", secret_resolver=lambda _: None, transport=httpx.MockTransport(handler))
    with pytest.raises(ConnectorError, match="configured in Glacier"):
        missing.test_connection()
    missing.close()


def test_jobber_refreshes_expired_oauth_token_and_saves_rotation():
    values = {"jobber_client_id": "client-id", "jobber_client_secret": "client-secret", "jobber_refresh_token": "refresh-old"}
    saved = []
    calls = []

    def handler(request):
        calls.append(request)
        if request.url.path == "/api/oauth/token":
            assert request.content.decode().find("client-secret") >= 0
            return httpx.Response(200, json={"access_token": "access-new", "refresh_token": "refresh-new"})
        if request.headers["Authorization"] == "Bearer expired":
            return httpx.Response(401)
        return httpx.Response(200, json={"data": {"account": {"id": "fixture-account", "name": "Fixture HVAC"}}})

    client = JobberClient(
        secret_resolver=lambda name: {"jobber_access_token": "expired"}.get(name, values.get(name)),
        secret_writer=lambda name, value: saved.append((name, value)),
        transport=httpx.MockTransport(handler),
        sleep=lambda _: None,
    )
    assert client.test_connection()["connected"] is True
    assert saved == [("jobber_access_token", "access-new"), ("jobber_refresh_token", "refresh-new")]
    assert [call.url.path for call in calls] == ["/api/graphql", "/api/oauth/token", "/api/graphql"]
    client.close()


def test_shopify_uses_saved_app_credentials_for_connection_and_saves_token():
    values = {"shopify_client_id": "shop-client", "shopify_client_secret": "shop-secret"}
    saved = []
    calls = []

    def handler(request):
        calls.append(request)
        if request.url.path == "/admin/oauth/access_token":
            return httpx.Response(200, json={"access_token": "shop-token", "expires_in": 86399})
        return httpx.Response(200, json={"data": {"shop": {"name": "Fixture Store", "myshopifyDomain": "fixture-store.myshopify.com"}}})

    client = ShopifyClient(
        "fixture-store.myshopify.com",
        secret_resolver=lambda name: values.get(name),
        secret_writer=lambda name, value: saved.append((name, value)),
        transport=httpx.MockTransport(handler),
    )
    assert client.test_connection()["connected"] is True
    assert saved == [("shopify_admin_access_token", "shop-token")]
    assert calls[1].headers["X-Shopify-Access-Token"] == "shop-token"
    client.close()
