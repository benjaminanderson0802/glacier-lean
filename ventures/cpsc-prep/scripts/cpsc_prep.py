"""Prepare, validate, and export CPSC Product Registry batches.

This module deliberately prepares files only. CPSC certification and submission
remain with the importer or their licensed customs broker.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.request import Request, urlopen


# These are the seven certificate elements in the current CPSC eFiling guide.
REQUIRED_FIELDS = (
    "product_id",
    "applicable_cpsc_rules",
    "manufacture_date",
    "manufacture_place",
    "last_test_date",
    "testing_lab",
    "records_contact",
)


def _value(record: Any) -> str:
    if not isinstance(record, Mapping):
        return "" if record is None else str(record).strip()
    value = record.get("value", "")
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    return str(value).strip()


def _month_date(value: Any) -> str:
    """Normalize an observed date to CPSC's YYYY-MM certificate date."""
    text = str(value or "").strip()
    if len(text) >= 7 and text[4] == "-" and text[:4].isdigit() and text[5:7].isdigit():
        return text[:7]
    return text


def _rules_fields(fields: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Map venture intake names to the merged ruleset's official CPSC names."""
    def raw(name: str) -> Any:
        return fields.get(name, {}).get("value", "")

    citations = [part.strip() for part in str(raw("applicable_cpsc_rules") or "").split(";") if part.strip()]
    manufacture = fields.get("manufacture_place", {})
    laboratory = fields.get("testing_lab", {})
    contact = fields.get("records_contact", {})
    manufacture = manufacture if isinstance(manufacture, dict) and "value" in manufacture else {"value": manufacture}
    laboratory = laboratory if isinstance(laboratory, dict) and "value" in laboratory else {"value": laboratory}
    contact = contact if isinstance(contact, dict) and "value" in contact else {"value": contact}
    manufacture_date = _month_date(raw("manufacture_date"))
    return {
        "product_id": fields.get("product_id", {}),
        "citation_codes": {"value": citations, "page": fields.get("applicable_cpsc_rules", {}).get("page"),
                            "confidence": fields.get("applicable_cpsc_rules", {}).get("confidence"),
                            "uncertain": fields.get("applicable_cpsc_rules", {}).get("uncertain", False)},
        "manufacture_date": {"value": manufacture_date, "page": fields.get("manufacture_date", {}).get("page"),
                             "confidence": fields.get("manufacture_date", {}).get("confidence"),
                             "uncertain": fields.get("manufacture_date", {}).get("uncertain", False)},
        "manufacture_place": manufacture,
        "product_test_date": fields.get("last_test_date", {}),
        "testing_laboratory": laboratory,
        "point_of_contact": contact,
    }


def _field_record(record: Any) -> dict[str, Any]:
    if isinstance(record, Mapping) and "value" in record:
        return {
            "value": record.get("value"),
            "page": record.get("page"),
            "confidence": record.get("confidence"),
            "uncertain": bool(record.get("uncertain", False)),
        }
    return {"value": record, "page": None, "confidence": None, "uncertain": False}


def _feed_rows(feeds: Any, source_id: str) -> list[dict[str, Any]]:
    """Refresh a configured source, then read its current records."""
    try:
        feeds.sync(source_id)
        rows = feeds.query(source_id)
    except KeyError:
        # An unregistered source is a release blocker, not a reason to crash or
        # fall back to stale/hard-coded government data.
        return []
    result = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        normalized = dict(row)
        data = row.get("data")
        if isinstance(data, Mapping):
            normalized.update(data)
        result.append(normalized)
    return result


def _codes(rows: list[dict[str, Any]], *keys: str) -> set[str]:
    result: set[str] = set()
    for row in rows:
        lower = {str(name).casefold(): value for name, value in row.items()}
        for key in keys:
            value = row.get(key, lower.get(key.casefold()))
            if value is not None and str(value).strip():
                result.add(str(value).strip())
                break
    return result


def _tariff_key(value: Any) -> str:
    return "".join(character for character in str(value or "") if character.isdigit())


def _read_documents(reader: Any, paths: list[str]) -> tuple[dict[str, dict[str, Any]], str]:
    extracted: dict[str, dict[str, Any]] = {}
    texts: list[str] = []
    for path in paths:
        result = reader.read_document(path, schema=list(REQUIRED_FIELDS))
        if isinstance(result, Mapping):
            text = result.get("text")
            if isinstance(text, str) and text.strip():
                texts.append(text)
            fields = result.get("fields", {})
            if isinstance(fields, Mapping):
                extracted.update({str(name): _field_record(field) for name, field in fields.items()})
    return extracted, "\n\n".join(texts)


def local_second_engine(product_id: str, source_text: str) -> Mapping[str, Any]:
    """Re-extract via configured local Ollama; absent/unavailable stays uncertain."""
    base_url = os.environ.get("GLACIER_OLLAMA_URL", "").strip()
    model = os.environ.get("GLACIER_LOCAL_MODEL", "").strip()
    if not base_url or not model or not source_text.strip():
        return {"fields": {}}
    prompt = (
        "Extract these CPSC certificate fields from the source text. Return only JSON "
        "with a fields object; each value must be a string, and use an empty string "
        "when the source does not state it. Do not infer or fill gaps. Fields: "
        + ", ".join(REQUIRED_FIELDS)
        + f". Product reference: {product_id}. Source text:\n{source_text}"
    )
    body = json.dumps({"model": model, "prompt": prompt, "stream": False, "format": "json", "options": {"temperature": 0}}).encode("utf-8")
    request = Request(base_url.rstrip("/") + "/api/generate", data=body, headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=120) as response:
        payload = json.loads(response.read().decode("utf-8"))
    generated = json.loads(payload.get("response", "{}"))
    raw_fields = generated.get("fields", generated)
    if not isinstance(raw_fields, Mapping):
        return {"fields": {}}
    return {"fields": {name: {"value": raw_fields.get(name, ""), "page": None, "confidence": None, "uncertain": False} for name in REQUIRED_FIELDS}}


def prepare_batch(
    batch: Mapping[str, Any],
    *,
    reader: Any,
    rules: Any,
    feeds: Any,
    ruleset: str,
    rule_codes_source: str,
    template_source: str,
    customer_certified: bool = False,
    flagged_codes_source: str = "cpsc_flagged_tariff_codes",
    second_engine: Callable[[str, str], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a customer-reviewable batch and optionally a template-exact CSV.

    `second_engine` must be an independently configured extraction engine and
    returns the same reader shape as read_document. The reader block has no
    second-engine operation in its fixed contract, so callers must inject it.
    Without it, extracted fields remain uncertain and cannot be exported.
    """
    batch_id = str(batch.get("batch_id", "")).strip()
    if not batch_id:
        raise ValueError("batch_id is required")
    products = batch.get("products")
    if not isinstance(products, list) or not products:
        raise ValueError("products must be a non-empty list")

    tariff_rows = _feed_rows(feeds, flagged_codes_source)
    rule_rows = _feed_rows(feeds, rule_codes_source)
    template_rows = _feed_rows(feeds, template_source)
    flagged_codes = {_tariff_key(code) for code in _codes(tariff_rows, "tariff_code", "code", "hts")}
    valid_rule_codes = _codes(rule_rows, "code", "rule_code", "citation", "citation_code", "citation codes", "citation / testing exception code")
    columns = template_rows[0].get("columns") if template_rows else None
    field_map = template_rows[0].get("field_map", {}) if template_rows else {}
    if not isinstance(field_map, Mapping):
        field_map = {}
    if not isinstance(columns, list) or not columns or not all(isinstance(col, str) for col in columns):
        return {
            "batch_id": batch_id,
            "importer_id": str(batch.get("importer_id", "unassigned")),
            "status": "uncertain — please check",
            "workflow_state": "customer_review_required",
            "csv": None,
            "csv_columns": [],
            "gaps": [{"field": "registry_template", "reason": "current CPSC template is unavailable"}],
            "products": [],
            "submission_performed": False,
        }

    processed: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    all_ready = True
    csv_rows: list[dict[str, str]] = []
    as_of = date.today().isoformat()

    for index, product in enumerate(products):
        if not isinstance(product, Mapping):
            raise ValueError(f"products[{index}] must be an object")
        product_id = str(product.get("product_id", "")).strip() or f"product-{index + 1}"
        documents = product.get("documents", [])
        if not isinstance(documents, list) or not all(isinstance(path, str) for path in documents):
            raise ValueError(f"products[{index}].documents must be a list of document paths")

        primary, source_text = _read_documents(reader, documents)
        if second_engine is not None:
            second_result = second_engine(product_id, source_text)
            second_fields = second_result.get("fields", {}) if isinstance(second_result, Mapping) else {}
            second = {str(name): _field_record(value) for name, value in second_fields.items()} if isinstance(second_fields, Mapping) else {}
        else:
            second = {}

        output_fields: dict[str, dict[str, Any]] = {}
        product_gaps: list[dict[str, Any]] = []
        for name in REQUIRED_FIELDS:
            first = primary.get(name)
            other = second.get(name)
            first_value = _value(first)
            second_value = _value(other)
            has_agreement = bool(first and other and first_value == second_value)
            uncertain = not has_agreement or bool(first and first.get("uncertain")) or bool(other and other.get("uncertain"))
            value = first.get("value") if first and first.get("value") is not None else ""
            field_result = {
                "value": value,
                "source": {"document": documents[0] if documents else None, "page": first.get("page") if first else None},
                "confidence": first.get("confidence") if first else None,
                "verdict": "uncertain" if uncertain else "match",
            }
            output_fields[name] = field_result
            if not value:
                product_gaps.append({"product_id": product_id, "field": name, "reason": "missing value; left blank"})
                # A blank required certificate element belongs in the gap list,
                # but it must also keep an incomplete registry file from being
                # released as ready for customer submission.
                all_ready = False
            if uncertain:
                product_gaps.append({"product_id": product_id, "field": name, "reason": "uncertain — please check; independent values do not agree" if other else "uncertain — please check; no independent second-engine result"})
                all_ready = False

        tariff_code = str(product.get("tariff_code", "")).strip()
        tariff_match = False
        if not flagged_codes:
            product_gaps.append({"product_id": product_id, "field": "tariff_code", "reason": "current CPSC flagged-code list is unavailable"})
            all_ready = False
        elif not tariff_code:
            product_gaps.append({"product_id": product_id, "field": "tariff_code", "reason": "missing tariff code; cannot check CPSC flagged-code list"})
            all_ready = False
        elif _tariff_key(tariff_code) not in flagged_codes:
            product_gaps.append({"product_id": product_id, "field": "tariff_code", "reason": "tariff code is not on the current CPSC flagged-code list"})
            all_ready = False
        else:
            tariff_match = True

        rule_text = output_fields["applicable_cpsc_rules"]["value"]
        product_rule_codes = [part.strip() for part in rule_text.split(";") if part.strip()]
        if not product_rule_codes or not valid_rule_codes or any(code not in valid_rule_codes for code in product_rule_codes):
            product_gaps.append({"product_id": product_id, "field": "applicable_cpsc_rules", "reason": "rule code is missing or absent from current CPSC rule-code list"})
            all_ready = False

        rule_fields = _rules_fields(primary)
        rule_result = rules.check(rule_fields, ruleset)
        if not isinstance(rule_result, Mapping) or rule_result.get("verdict") != "pass":
            product_gaps.append({"product_id": product_id, "field": "rules", "reason": "rules checker did not return pass"})
            field_by_rule = {
                "cpsc.product_id": "product_id", "cpsc.citation_codes": "applicable_cpsc_rules",
                "cpsc.manufacture_date": "manufacture_date", "cpsc.manufacture_place": "manufacture_place",
                "cpsc.product_test_date": "last_test_date", "cpsc.testing_laboratory": "testing_lab",
                "cpsc.point_of_contact": "records_contact",
            }
            for issue in rule_result.get("results", []) if isinstance(rule_result, Mapping) else []:
                if issue.get("verdict") != "pass":
                    product_gaps.append({"product_id": product_id,
                                         "field": field_by_rule.get(str(issue.get("rule")), "rules"),
                                         "rule": issue.get("rule"), "reason": issue.get("detail", "CPSC field needs review")})
            all_ready = False

        row = {column: "" for column in columns}
        for name in REQUIRED_FIELDS:
            value = output_fields[name]["value"]
            targets: dict[str, Any] = {}
            direct = field_map.get(name)
            if direct:
                targets[str(direct)] = value
            elif isinstance(value, Mapping):
                for subfield, subvalue in value.items():
                    column = field_map.get(f"{name}.{subfield}")
                    if column:
                        targets[str(column)] = subvalue
            if not targets:
                product_gaps.append({"product_id": product_id, "field": name, "reason": "required field has no matching column in the current CPSC template"})
                all_ready = False
            for target_column, cell_value in targets.items():
                if target_column not in row:
                    product_gaps.append({"product_id": product_id, "field": name, "reason": "required field has no matching column in the current CPSC template"})
                    all_ready = False
                else:
                    if name == "manufacture_date":
                        cell_value = _month_date(cell_value)
                        if len(cell_value) == 7 and cell_value[4] == "-":
                            cell_value = f"{cell_value[5:7]}/{cell_value[:4]}"
                    row[target_column] = json.dumps(cell_value, ensure_ascii=False) if isinstance(cell_value, (dict, list)) else str(cell_value)
        # Product identifiers that are present in the official template are copied;
        # no value is fabricated to fill other columns.
        tariff_column = str(field_map.get("tariff_code", "tariff_code"))
        if tariff_column in row:
            row[tariff_column] = tariff_code
        for column, value in row.items():
            if value == "" and not any(gap["field"] == column for gap in product_gaps):
                source_field = next((name for name, mapped in field_map.items() if mapped == column), column)
                product_gaps.append({"product_id": product_id, "field": str(source_field), "template_column": column, "reason": "missing value; left blank"})
        csv_rows.append(row)
        gaps.extend(product_gaps)
        product_result = (
            f"no match found in CPSC flagged tariff-code list as of {as_of}"
            if tariff_code and flagged_codes and not tariff_match
            else "match" if not product_gaps
            else "uncertain — please check"
        )
        processed.append({"product_id": product_id, "tariff_code": tariff_code, "result": product_result, "fields": output_fields, "rules": dict(rule_result) if isinstance(rule_result, Mapping) else {}})

    if not customer_certified:
        workflow_state = "awaiting_customer_certification"
    else:
        workflow_state = "ready_for_customer_submission" if all_ready else "customer_review_required"

    if processed and all(product["result"].startswith("no match found in CPSC flagged tariff-code list") for product in processed):
        status = f"no match found in CPSC flagged tariff-code list as of {as_of}"
    elif not gaps and all_ready and customer_certified:
        status = "match"
    else:
        status = "uncertain — please check"

    csv_text: str | None = None
    if customer_certified and all_ready:
        output = __import__("io").StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(csv_rows)
        csv_text = output.getvalue()

    return {
        "batch_id": batch_id,
        "importer_id": str(batch.get("importer_id", "unassigned")),
        "generated_at": as_of,
        "status": status,
        "workflow_state": workflow_state,
        "csv": csv_text,
        "csv_columns": columns,
        "gaps": gaps,
        "products": processed,
        "submission_performed": False,
    }


def load_blocks() -> tuple[Any, Any, Any]:
    """Import the shared blocks by their fixed, documented package contract."""
    try:
        from ventures.blocks.reader import read_document as reader_read_document
        from ventures.blocks.rules import check as rules_check
        from ventures.blocks.feeds import query as feeds_query, sync as feeds_sync
    except ImportError as exc:
        raise RuntimeError("CPSC prep requires the reader, rules, and feeds blocks from ventures.blocks") from exc

    reader_function = read_document
    rules_function = check
    query_function = query
    sync_function = sync

    class Reader:
        read_document = staticmethod(reader_read_document)

    class Rules:
        check = staticmethod(rules_check)

    class Feeds:
        query = staticmethod(feeds_query)
        sync = staticmethod(feeds_sync)

    return Reader(), Rules(), Feeds()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare a customer-reviewable CPSC Product Registry batch")
    parser.add_argument("batch_json", type=Path)
    parser.add_argument("--ruleset", default="cpsc_efiling.json")
    parser.add_argument("--rule-codes-source", default="cpsc_rule_codes")
    parser.add_argument("--flagged-codes-source", default="cpsc_flagged_tariff_codes")
    parser.add_argument("--template-source", default="cpsc_registry_template")
    parser.add_argument("--customer-certified", action="store_true", help="set only after customer's field-by-field review and certification")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--csv-out", type=Path)
    args = parser.parse_args(argv)
    try:
        batch = json.loads(args.batch_json.read_text(encoding="utf-8"))
        reader, rules, feeds = load_blocks()
        result = prepare_batch(
            batch,
            reader=reader,
            rules=rules,
            feeds=feeds,
            ruleset=args.ruleset,
            rule_codes_source=args.rule_codes_source,
            flagged_codes_source=args.flagged_codes_source,
            template_source=args.template_source,
            customer_certified=args.customer_certified,
            second_engine=local_second_engine,
        )
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if args.csv_out and result["csv"] is not None:
            args.csv_out.parent.mkdir(parents=True, exist_ok=True)
            args.csv_out.write_text(result["csv"], encoding="utf-8", newline="")
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"cpsc-prep: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
