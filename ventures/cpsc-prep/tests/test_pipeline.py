"""Acceptance checks for the CPSC batch-preparation workflow."""

from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from cpsc_prep import REQUIRED_FIELDS, local_second_engine, prepare_batch


class FakeReader:
    def __init__(self, records):
        self.records = records
        self.calls = []

    def read_document(self, path, schema=None):
        self.calls.append((path, schema))
        return {"fields": self.records[path], "text": "fixture"}


class FakeRules:
    def check(self, fields, ruleset):
        rule_codes = fields.get("applicable_cpsc_rules", {}).get("value", "")
        verdict = "pass" if rule_codes == "16 CFR 1501" else "fail"
        return {
            "verdict": verdict,
            "results": [{"rule": "cpsc-rule-codes", "verdict": verdict, "cite": "fixture", "detail": rule_codes}],
        }


class FakeFeeds:
    def __init__(self):
        self.synced = []
        self.queried = []

    def sync(self, source_id):
        self.synced.append(source_id)
        return {"rows": [], "changed": False, "alerts": []}

    def query(self, source_id, **filters):
        self.queried.append((source_id, filters))
        if source_id == "cpsc_registry_template":
            return [{"columns": list(REQUIRED_FIELDS)}]
        if source_id == "cpsc_rule_codes":
            return [{"code": "16 CFR 1501"}]
        if source_id == "cpsc_flagged_tariff_codes":
            return [{"tariff_code": "9503.00.00"}]
        return []


def fields(values):
    return {
        key: {"value": value, "page": 1, "confidence": 0.99, "uncertain": False}
        for key, value in values.items()
    }


def good_values():
    return {
        "product_id": "SKU-001",
        "applicable_cpsc_rules": "16 CFR 1501",
        "manufacture_date": "2026-01-02",
        "manufacture_place": "Dayton, OH",
        "manufacturer": "Example Works",
        "last_test_date": "2026-03-04",
        "last_test_place": "Dayton, OH",
        "testing_lab": "Example Lab",
        "records_contact": "records@example.test",
    }


def fake_second_engine(reader):
    """Independent test double; production must inject its second engine."""
    return lambda product_id, documents: {"fields": reader.records["crosscheck.json"]}


def test_missing_required_values_stay_blank_in_review_data_and_block_registry_export():
    values = good_values()
    values["manufacturer"] = ""
    source = fields(values)
    second = fields(values)
    reader = FakeReader({"lab.pdf": source, "crosscheck.json": second})
    feeds = FakeFeeds()

    result = prepare_batch(
        {"batch_id": "B-1", "products": [{"product_id": "SKU-001", "tariff_code": "9503.00.00", "documents": ["lab.pdf"]}]},
        reader=reader,
        rules=FakeRules(),
        feeds=feeds,
        ruleset="cpsc-current",
        rule_codes_source="cpsc_rule_codes",
        template_source="cpsc_registry_template",
        customer_certified=True,
        second_engine=fake_second_engine(reader),
    )

    assert result["status"] == "uncertain — please check"
    assert result["submission_performed"] is False
    assert result["csv_columns"] == list(REQUIRED_FIELDS)
    assert result["csv"] is None
    assert any(gap["field"] == "manufacturer" for gap in result["gaps"])
    assert result["products"][0]["fields"]["product_id"]["source"]["page"] == 1
    assert feeds.synced == ["cpsc_flagged_tariff_codes", "cpsc_rule_codes", "cpsc_registry_template"]


def test_agreed_complete_fields_generate_exact_template_csv():
    values = good_values()
    reader = FakeReader({"lab.pdf": fields(values), "crosscheck.json": fields(values)})
    result = prepare_batch(
        {"batch_id": "B-8", "products": [{"product_id": "SKU-001", "tariff_code": "9503.00.00", "documents": ["lab.pdf"]}]},
        reader=reader,
        rules=FakeRules(),
        feeds=FakeFeeds(),
        ruleset="cpsc-current",
        rule_codes_source="cpsc_rule_codes",
        template_source="cpsc_registry_template",
        customer_certified=True,
        second_engine=fake_second_engine(reader),
    )

    assert result["status"] == "match"
    assert result["workflow_state"] == "ready_for_customer_submission"
    assert result["csv_columns"] == list(REQUIRED_FIELDS)
    assert list(csv.DictReader(io.StringIO(result["csv"]))) == [values]
    assert result["submission_performed"] is False


def test_disagreement_and_uncited_rule_codes_remain_uncertain_and_do_not_export_as_ready():
    first = good_values()
    second = good_values() | {"manufacturer": "Other Manufacturer"}
    reader = FakeReader({"lab.pdf": fields(first), "crosscheck.json": fields(second)})

    result = prepare_batch(
        {"batch_id": "B-2", "products": [{"product_id": "SKU-001", "tariff_code": "9503.00.00", "documents": ["lab.pdf"]}]},
        reader=reader,
        rules=FakeRules(),
        feeds=FakeFeeds(),
        ruleset="cpsc-current",
        rule_codes_source="cpsc_rule_codes",
        template_source="cpsc_registry_template",
        customer_certified=True,
        second_engine=fake_second_engine(reader),
    )

    assert result["status"] == "uncertain — please check"
    assert result["products"][0]["fields"]["manufacturer"]["verdict"] == "uncertain"
    assert result["csv"] is None
    assert result["submission_performed"] is False


def test_no_second_engine_never_claims_model_values_are_agreed():
    reader = FakeReader({"lab.pdf": fields(good_values())})
    result = prepare_batch(
        {"batch_id": "B-3", "products": [{"product_id": "SKU-001", "tariff_code": "9503.00.00", "documents": ["lab.pdf"]}]},
        reader=reader,
        rules=FakeRules(),
        feeds=FakeFeeds(),
        ruleset="cpsc-current",
        rule_codes_source="cpsc_rule_codes",
        template_source="cpsc_registry_template",
        customer_certified=True,
    )
    assert result["status"] == "uncertain — please check"
    assert all(result["products"][0]["fields"][name]["verdict"] == "uncertain" for name in REQUIRED_FIELDS)
    assert result["csv"] is None


def test_cli_local_second_engine_stays_unavailable_without_local_model(monkeypatch):
    monkeypatch.delenv("GLACIER_OLLAMA_URL", raising=False)
    monkeypatch.delenv("GLACIER_LOCAL_MODEL", raising=False)
    assert local_second_engine("SKU-001", "certificate source") == {"fields": {}}


def test_unknown_cpsc_rule_code_blocks_export_even_after_customer_certification():
    values = good_values() | {"applicable_cpsc_rules": "16 CFR 9999"}
    reader = FakeReader({"lab.pdf": fields(values), "crosscheck.json": fields(values)})
    result = prepare_batch(
        {"batch_id": "B-4", "products": [{"product_id": "SKU-001", "tariff_code": "9503.00.00", "documents": ["lab.pdf"]}]},
        reader=reader,
        rules=FakeRules(),
        feeds=FakeFeeds(),
        ruleset="cpsc-current",
        rule_codes_source="cpsc_rule_codes",
        template_source="cpsc_registry_template",
        customer_certified=True,
        second_engine=fake_second_engine(reader),
    )
    assert result["status"] == "uncertain — please check"
    assert result["csv"] is None
    assert any("rule" in gap["reason"] for gap in result["gaps"])


def test_missing_cpsc_feed_is_uncertain_not_a_no_match():
    class EmptyFlaggedCodes(FakeFeeds):
        def query(self, source_id, **filters):
            if source_id == "cpsc_flagged_tariff_codes":
                return []
            return super().query(source_id, **filters)

    values = good_values()
    reader = FakeReader({"lab.pdf": fields(values)})
    result = prepare_batch(
        {"batch_id": "B-6", "products": [{"product_id": "SKU-001", "tariff_code": "9503.00.00", "documents": ["lab.pdf"]}]},
        reader=reader,
        rules=FakeRules(),
        feeds=EmptyFlaggedCodes(),
        ruleset="cpsc-current",
        rule_codes_source="cpsc_rule_codes",
        template_source="cpsc_registry_template",
        customer_certified=True,
    )
    assert result["status"] == "uncertain — please check"
    assert not result["status"].startswith("no match")
    assert result["csv"] is None


def test_uncertified_customer_cannot_get_registry_upload():
    values = good_values()
    reader = FakeReader({"lab.pdf": fields(values), "crosscheck.json": fields(values)})
    result = prepare_batch(
        {"batch_id": "B-5", "products": [{"product_id": "SKU-001", "tariff_code": "9503.00.00", "documents": ["lab.pdf"]}]},
        reader=reader,
        rules=FakeRules(),
        feeds=FakeFeeds(),
        ruleset="cpsc-current",
        rule_codes_source="cpsc_rule_codes",
        template_source="cpsc_registry_template",
        customer_certified=False,
        second_engine=fake_second_engine(reader),
    )
    assert result["status"] == "uncertain — please check"
    assert result["csv"] is None
    assert result["submission_performed"] is False
