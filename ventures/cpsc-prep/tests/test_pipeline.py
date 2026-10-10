"""Acceptance checks for the CPSC batch-preparation workflow."""

from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from cpsc_prep import REQUIRED_FIELDS, _rules_fields, local_second_engine, prepare_batch
from ventures.blocks.rules.checker import check as check_official_rules

TEMPLATE_MAP = {
    "product_id": "Primary Product ID", "applicable_cpsc_rules": "Lab 1 Citation Codes",
    "manufacture_date": "Manufacture Date", "manufacture_place.name": "Manufacturer Name",
    "manufacture_place.address": "Manufacturer Address Line 1", "manufacture_place.contact": "Manufacturer Email",
    "last_test_date": "Last Test Date", "testing_lab.name": "Lab 1 Name",
    "testing_lab.address": "Lab 1 Address Line 1", "testing_lab.contact": "Lab 1 Email",
    "records_contact.name": "POC Name", "records_contact.address": "POC Address Line 1",
    "records_contact.contact": "POC Email",
}
TEMPLATE_COLUMNS = list(TEMPLATE_MAP.values()) + ["tariff_code"]


class FakeReader:
    def __init__(self, records):
        self.records = records
        self.calls = []

    def read_document(self, path, schema=None):
        self.calls.append((path, schema))
        return {"fields": self.records[path], "text": "fixture"}


class FakeRules:
    def check(self, fields, ruleset):
        return check_official_rules(fields, "cpsc_efiling.json")


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
            return [{"columns": TEMPLATE_COLUMNS, "field_map": TEMPLATE_MAP}]
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
        "manufacture_place": {"name": "Example Works", "address": "10 Factory Way, Dayton, OH", "contact": "factory@example.test"},
        "last_test_date": "2026-03-04",
        "testing_lab": {"name": "Example Lab", "address": "20 Test Way, Dayton, OH", "contact": "lab@example.test"},
        "records_contact": {"name": "Records Desk", "address": "10 Factory Way, Dayton, OH", "contact": "records@example.test"},
    }


def fake_second_engine(reader):
    """Independent test double; production must inject its second engine."""
    return lambda product_id, documents: {"fields": reader.records["crosscheck.json"]}


def test_missing_required_values_stay_blank_in_review_data_and_block_registry_export():
    values = good_values()
    values["records_contact"] = {"name": "", "address": "10 Factory Way, Dayton, OH", "contact": "records@example.test"}
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
    assert result["csv_columns"] == TEMPLATE_COLUMNS
    assert result["csv"] is None
    assert any(gap["field"] == "records_contact" for gap in result["gaps"])
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
    assert result["csv_columns"] == TEMPLATE_COLUMNS
    exported = next(csv.DictReader(io.StringIO(result["csv"])))
    assert exported["Manufacturer Name"] == values["manufacture_place"]["name"]
    assert exported["Manufacturer Address Line 1"] == values["manufacture_place"]["address"]
    assert exported["Lab 1 Name"] == values["testing_lab"]["name"]
    assert exported["POC Email"] == values["records_contact"]["contact"]
    assert exported["Manufacture Date"] == "01/2026"
    assert result["submission_performed"] is False


def test_disagreement_and_uncited_rule_codes_remain_uncertain_and_do_not_export_as_ready():
    first = good_values()
    second = good_values() | {"manufacture_place": {"name": "Other Manufacturer", "address": "10 Factory Way", "contact": "factory@example.test"}}
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
    assert result["products"][0]["fields"]["manufacture_place"]["verdict"] == "uncertain"
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


def test_current_seven_cpsc_elements_map_to_the_merged_ruleset():
    values = fields(good_values())
    checked = check_official_rules(_rules_fields(values), "cpsc_efiling.json")
    assert checked["verdict"] == "pass"
    assert {item["rule"] for item in checked["results"]} == {
        "cpsc.product_id", "cpsc.citation_codes", "cpsc.manufacture_date", "cpsc.manufacture_place",
        "cpsc.product_test_date", "cpsc.testing_laboratory", "cpsc.point_of_contact",
    }
    incomplete = fields(good_values())
    incomplete["testing_lab"]["value"].pop("contact")
    assert check_official_rules(_rules_fields(incomplete), "cpsc_efiling.json")["verdict"] == "fail"


def test_all_cpsc_reference_source_ids_are_registered():
    from ventures.blocks.feeds import core as feeds

    sources = feeds.registry()
    assert {"cpsc_flagged_tariff_codes", "cpsc_rule_codes", "cpsc_registry_template"} <= sources.keys()
    assert all(sources[key]["kind"] == "cpsc_document" for key in (
        "cpsc_flagged_tariff_codes", "cpsc_rule_codes", "cpsc_registry_template"))


def test_refresh_block_loader_exposes_reader_rules_and_feeds():
    from cpsc_prep import load_blocks

    reader, rules, feeds = load_blocks()
    assert callable(reader.read_document)
    assert callable(rules.check)
    assert callable(feeds.sync)
    assert callable(feeds.query)


def test_source_refresh_reports_integrated_feed_row_counts(monkeypatch, capsys):
    import refresh_cpsc_sources

    class Feeds:
        def sync(self, source_id):
            return {"rows": 7, "changed": False, "alerts": []}

    monkeypatch.setattr(refresh_cpsc_sources, "load_blocks", lambda: (None, None, Feeds()))
    assert refresh_cpsc_sources.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert set(report["sources"]) == {
        "cpsc_flagged_tariff_codes", "cpsc_rule_codes", "cpsc_registry_template"
    }
    assert all(source["row_count"] == 7 for source in report["sources"].values())


def test_owner_gates_link_lawyer_batch_certification_and_contract_steps():
    manifest = json.loads((Path(__file__).resolve().parents[1] / "venture.json").read_text(encoding="utf-8"))
    steps = {step["id"]: step for step in manifest["your_steps"]}
    assert "written confirmation" in steps["trade-lawyer-opinion"]["detail"]
    assert "https://www.cpsc.gov/efiling/importers" in steps["trade-lawyer-opinion"]["links"]
    assert "certify as the importer" in steps["customer-certification"]["detail"]
    assert "https://www.cpsc.gov/eFiling-Document-Library" in steps["first-broker-contract"]["links"]
    assert "GLACIER_OLLAMA_URL" in steps["first-broker-contract"]["detail"]
    assert "test-mode key" in steps["first-broker-contract"]["detail"]


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
