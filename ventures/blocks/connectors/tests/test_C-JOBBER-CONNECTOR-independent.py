"""Independent offline checks for the Jobber-to-venture mapping boundary."""
from __future__ import annotations

import importlib.util
import json
import re
from datetime import date
from pathlib import Path

import httpx
import pytest

from ventures.blocks.connectors import JobberClient
from ventures.blocks.connectors.clients import JOBBER_GRAPHQL_URL
from ventures.blocks.connectors.common import ConnectorError


ROOT = Path(__file__).resolve().parents[4]

CONNECTION_QUERY = "query ConnectionCheck { account { id name } }"
JOBS_QUERY = """query ReadJobs($first: Int!, $after: String) {
          jobs(first: $first, after: $after) {
            nodes {
              id jobNumber title jobStatus completedAt jobberWebUri
              customFields {
                __typename
                ... on CustomFieldText { id label valueText }
              }
              client { id name email }
              property { id address { city province postalCode country } }
            }
            pageInfo { hasNextPage endCursor }
          }
        }"""


def _normalized_query(query):
    return re.sub(r"\s+", " ", query).strip()


def _load_module(relative_path: str, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, ROOT / relative_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


closeout = _load_module("ventures/job-closeout/scripts/generate_packet.py", "jobber_connector_closeout")
warranty = _load_module("ventures/warranty/scripts/warranty.py", "jobber_connector_warranty")


def _job(**overrides):
    job = {
        "id": "Z2lkOi8vSm9iYmVyL0pvYi85MDAx",
        "jobNumber": 9001,
        "title": "Heat pump installation",
        "jobStatus": "COMPLETED",
        "completedAt": "2026-03-20T15:30:00-05:00",
        "customFields": [
            {"__typename": "CustomFieldText", "id": "field-brand", "label": "Equipment Brand", "valueText": "Carrier"},
            {"__typename": "CustomFieldText", "id": "field-model", "label": "Equipment Model", "valueText": "Infinity 24"},
            {"__typename": "CustomFieldText", "id": "field-serial", "label": "Equipment Serial", "valueText": "ABC123456789"},
            {"__typename": "CustomFieldText", "id": "field-date", "label": "Install Date", "valueText": "2026-03-20"},
        ],
        "client": {"id": "Z2lkOi8vSm9iYmVyL0NsaWVudC8yMDAx", "name": "Maya Rivera", "email": "maya@example.test"},
        "property": {
            "id": "Z2lkOi8vSm9iYmVyL1Byb3BlcnR5LzMwMDE",
            "address": {"city": "Austin", "province": "TX", "postalCode": "78701", "country": "US"},
        },
    }
    job.update(overrides)
    return job


def _page(jobs, *, has_next_page=False, end_cursor=None):
    return {"data": {"jobs": {"nodes": jobs, "pageInfo": {"hasNextPage": has_next_page, "endCursor": end_cursor}}}}


def _client(responses, seen=None):
    seen = seen if seen is not None else []

    def handler(request):
        seen.append(request)
        assert request.url == httpx.URL(JOBBER_GRAPHQL_URL)
        assert request.method == "POST"
        assert request.headers.get("X-JOBBER-GRAPHQL-VERSION") == "2026-04-16"
        body = json.loads(request.content)
        query = body["query"]
        assert _normalized_query(query) in {
            _normalized_query(CONNECTION_QUERY),
            _normalized_query(JOBS_QUERY),
        }
        return httpx.Response(200, json=responses.pop(0))

    client = JobberClient(
        access_token="synthetic-token",
        transport=httpx.MockTransport(handler),
        sleep=lambda _: None,
    )
    return client, seen


def test_C_JOBBER_CONNECTOR_completed_fixture_preserves_packet_mapping_and_provenance():
    response = _page([_job()])
    seen = []
    client, _ = _client([
        {"data": {"account": {"id": "fixture-account", "name": "Fixture HVAC"}}},
        response,
    ], seen)
    try:
        account = client.test_connection()
        records = client.get_jobs(max_pages=1)
    finally:
        client.close()

    assert account == {"connected": True, "account": "Fixture HVAC"}
    assert len(seen) == 2
    assert [request.url.host for request in seen] == ["api.getjobber.com", "api.getjobber.com"]
    record = records[0]
    assert record["id"] == record["job_id"] == "Z2lkOi8vSm9iYmVyL0pvYi85MDAx"
    assert record["client"]["id"] == "Z2lkOi8vSm9iYmVyL0NsaWVudC8yMDAx"
    assert record["property"]["id"] == "Z2lkOi8vSm9iYmVyL1Byb3BlcnR5LzMwMDE"
    assert record["customFields"][0]["id"] == "field-brand"
    assert record["jobStatus"] == "COMPLETED"
    assert record["completedAt"] == "2026-03-20T15:30:00-05:00"
    packet = closeout.build_packet(record, account["account"])
    assert packet["job_id"] == "Z2lkOi8vSm9iYmVyL0pvYi85MDAx"
    assert packet["job_number"] == "9001"
    assert packet["completion_status"] == "completed"
    assert packet["completion_date"] == "2026-03-20"
    assert packet["customer_name"] == "Maya Rivera"
    assert packet["equipment"] == [{"brand": "Carrier", "model": "Infinity 24", "serial": "ABC123456789"}]
    assert packet["business_name"] == "Fixture HVAC"

    loop = warranty.build_jobber_loop(records, as_of=date(2026, 3, 21))
    assert loop["source"] == "Jobber read-only GraphQL API"
    unit = loop["units"][0]
    assert unit["job_id"] == packet["job_id"]
    assert unit["job_number"] == 9001
    assert unit["completed"] is True
    assert unit["intake_source"] == "Jobber read-only"
    assert loop["registration_queue"][0]["job_id"] == packet["job_id"]
    assert loop["registration_queue"][0]["intake_source"] == "Jobber read-only"
    assert loop["homeowner_email_drafts"][0]["job_id"] == packet["job_id"]
    assert loop["homeowner_email_drafts"][0]["sent"] is False


def test_C_JOBBER_CONNECTOR_null_optional_fields_remain_uncertain_downstream():
    job = _job(jobNumber=None, title=None, completedAt=None, jobStatus="COMPLETED", client={"id": "client-id", "name": None, "email": None}, customFields=[])
    client, _ = _client([_page([job])])
    try:
        records = client.get_jobs(max_pages=1)
    finally:
        client.close()

    packet = closeout.build_packet(records[0], "Fixture HVAC")
    assert packet["job_id"] == job["id"]
    assert packet["completion_status"] == "completed"
    assert packet["job_number"] == closeout.UNCERTAIN
    assert packet["job_title"] == closeout.UNCERTAIN
    assert packet["completion_date"] == closeout.UNCERTAIN
    assert packet["customer_name"] == closeout.UNCERTAIN
    assert packet["equipment"] == []

    loop = warranty.build_jobber_loop(records, as_of=date(2026, 3, 21))
    unit = loop["units"][0]
    assert unit["job_id"] == job["id"]
    assert unit["completed"] is True
    assert loop["registration_queue"][0]["result"].startswith("uncertain")
    assert loop["homeowner_email_drafts"] == []


def test_C_JOBBER_CONNECTOR_missing_permission_fails_closed_without_records():
    client = JobberClient(
        access_token="synthetic-token",
        transport=httpx.MockTransport(lambda request: httpx.Response(403, json={"message": "permission denied"})),
        sleep=lambda _: None,
    )
    try:
        with pytest.raises(ConnectorError, match="HTTP 403"):
            client.get_jobs(max_pages=1)
    finally:
        client.close()


def test_C_JOBBER_CONNECTOR_graphql_partial_data_fails_closed():
    client, _ = _client([{"data": {"jobs": {"nodes": [_job()], "pageInfo": {"hasNextPage": False}}}, "errors": [{"message": "field unavailable"}]}])
    try:
        with pytest.raises(ConnectorError, match="rejected the read query"):
            client.get_jobs(max_pages=1)
    finally:
        client.close()


def test_C_JOBBER_CONNECTOR_page_limit_never_returns_partial_records():
    client, _ = _client([_page([_job()], has_next_page=True, end_cursor="cursor-1")])
    try:
        with pytest.raises(ConnectorError, match="configured page limit"):
            client.get_jobs(max_pages=1)
    finally:
        client.close()


def test_C_JOBBER_CONNECTOR_write_attempt_is_refused_before_transport():
    calls = []
    client = JobberClient(
        access_token="synthetic-token",
        transport=httpx.MockTransport(lambda request: calls.append(request)),
        sleep=lambda _: None,
    )
    try:
        with pytest.raises(ConnectorError, match="read-only"):
            client.graphql("mutation UnsafeWrite { jobUpdate(input: {}) { job { id } } }")
    finally:
        client.close()
    assert calls == []
