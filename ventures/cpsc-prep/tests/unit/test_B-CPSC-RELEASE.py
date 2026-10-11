"""Release-boundary checks for CPSC registry template revisions."""

from __future__ import annotations

import sys
import json
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from cpsc_prep import prepare_batch
from ventures.blocks.rules.checker import check as check_official_rules


FIELD_MAP = {
    "product_id": "Primary Product ID",
    "applicable_cpsc_rules": "Lab 1 Citation Codes",
    "manufacture_date": "Manufacture Date",
    "manufacture_place.name": "Manufacturer Name",
    "manufacture_place.address": "Manufacturer Address Line 1",
    "manufacture_place.contact": "Manufacturer Email",
    "last_test_date": "Last Test Date",
    "testing_lab.name": "Lab 1 Name",
    "testing_lab.address": "Lab 1 Address Line 1",
    "testing_lab.contact": "Lab 1 Email",
    "records_contact.name": "POC Name",
    "records_contact.address": "POC Address Line 1",
    "records_contact.contact": "POC Email",
    "tariff_code": "Tariff Code",
}
COLUMNS = list(FIELD_MAP.values())
VALUES = {
    "product_id": "SKU-1",
    "applicable_cpsc_rules": "16 CFR 1501",
    "manufacture_date": "2026-01-02",
    "manufacture_place": {"name": "Factory", "address": "10 Factory Way, Dayton, OH", "contact": "factory@example.test"},
    "last_test_date": "2026-03-04",
    "testing_lab": {"name": "Lab", "address": "20 Test Way, Dayton, OH", "contact": "lab@example.test"},
    "records_contact": {"name": "Records", "address": "10 Factory Way, Dayton, OH", "contact": "records@example.test"},
}


class Reader:
    def read_document(self, path, schema=None):
        return {
            "fields": {
                name: {"value": value, "page": 1, "confidence": 1, "uncertain": False}
                for name, value in VALUES.items()
            },
            "text": "fixture",
        }


class Rules:
    def check(self, fields, ruleset):
        return check_official_rules(fields, "cpsc_efiling.json")


class Feeds:
    def __init__(self, *, template_columns=None, template_field_map=None, template_changed=False, required_columns=None):
        self.template_columns = template_columns or COLUMNS
        self.template_field_map = template_field_map or FIELD_MAP
        self.template_changed = template_changed
        self.required_columns = required_columns or []

    def sync(self, source_id):
        changed = self.template_changed and source_id == "cpsc_registry_template"
        return {"rows": 1, "changed": changed, "status": "ok", "alerts": []}

    def query(self, source_id, **filters):
        if source_id == "cpsc_registry_template":
            data = {"columns": self.template_columns, "field_map": self.template_field_map}
            if self.required_columns:
                data["required_columns"] = self.required_columns
            return [{
                "source_id": source_id,
                "record_id": "template-v3",
                "source_url": "https://cpsc.example/template",
                "fetched_at": "2026-10-10T12:00:00Z",
                "data": data,
            }]
        if source_id == "cpsc_rule_codes":
            return [{"source_id": source_id, "record_id": "rule-1", "data": {"code": "16 CFR 1501"}}]
        if source_id == "cpsc_flagged_tariff_codes":
            return [{"source_id": source_id, "record_id": "hts-1", "data": {"tariff_code": "9503.00.00"}}]
        return []


def run(feeds):
    return prepare_batch(
        {"batch_id": "B-RELEASE", "products": [{"product_id": "SKU-1", "tariff_code": "9503.00.00", "documents": ["lab.pdf"]}]},
        reader=Reader(),
        rules=Rules(),
        feeds=feeds,
        ruleset="cpsc-current",
        rule_codes_source="cpsc_rule_codes",
        template_source="cpsc_registry_template",
        customer_certified=True,
        second_engine=lambda product_id, source_text: {
            "fields": {
                name: {"value": value, "page": 1, "confidence": 1, "uncertain": False}
                for name, value in VALUES.items()
            }
        },
    )


def test_changed_template_revision_blocks_registry_csv_and_cites_local_revision():
    result = run(Feeds(template_changed=True))

    assert result["csv"] is None
    assert result["workflow_state"] == "customer_review_required"
    assert result["template_revision"]["status"] == "review_required"
    assert result["template_revision"]["source_id"] == "cpsc_registry_template"
    assert result["template_revision"]["revision"].startswith("sha256:")
    assert result["template_revision"]["source_url"] == "https://cpsc.example/template"


@pytest.mark.parametrize("columns", [COLUMNS[1:], [*COLUMNS, "New Required Element"]])
def test_removed_or_added_required_template_column_blocks_registry_csv(columns):
    required = ["New Required Element"] if "New Required Element" in columns else []
    result = run(Feeds(template_columns=columns, required_columns=required))

    assert result["csv"] is None
    assert result["workflow_state"] == "customer_review_required"
    assert any(gap["field"] == "registry_template" for gap in result["gaps"])


def test_unchanged_approved_revision_preserves_exact_column_order_and_is_deterministic():
    feeds = Feeds()

    first = run(feeds)
    second = run(feeds)

    assert first["csv_columns"] == COLUMNS
    assert first["csv"].splitlines()[0] == ",".join(COLUMNS)
    assert first["template_revision"]["status"] == "validated"
    assert first["template_revision"] == second["template_revision"]
    assert first == second


def test_source_refresh_reports_changed_revision_for_review(monkeypatch, capsys):
    import refresh_cpsc_sources

    class RefreshFeeds(Feeds):
        def sync(self, source_id):
            return {
                "rows": 1,
                "changed": source_id == "cpsc_registry_template",
                "status": "ok",
                "alerts": [],
            }

    feeds = RefreshFeeds()
    monkeypatch.setattr(refresh_cpsc_sources, "load_blocks", lambda: (None, None, feeds))

    assert refresh_cpsc_sources.main() == 1
    report = json.loads(capsys.readouterr().out)
    template = report["sources"]["cpsc_registry_template"]
    assert template["local_revision"].startswith("sha256:")
    assert "cpsc_registry_template" in report["review_required_before_release"]
