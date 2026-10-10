"""Recall-checking glue over the shared government-feed interface."""
from __future__ import annotations

import csv
import difflib
import html
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from ventures.blocks.feeds import query as query_feed


SOURCES = ("cpsc_recalls", "nhtsa_recalls", "fda_enforcement", "fsis_recalls")
SOURCE_LABELS = "CPSC, NHTSA, FDA and FSIS"
MATCH_RULESET = "recall-matching-v1"


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").casefold())


def _data(record: dict[str, Any]) -> dict[str, Any]:
    value = record.get("data")
    return value if isinstance(value, dict) else record


def _first(record: dict[str, Any], *names: str) -> str:
    fields = {str(k).casefold(): v for k, v in record.items()}
    for name in names:
        value = record.get(name, fields.get(name.casefold()))
        if value not in (None, "", []):
            return str(value).strip()
    return ""


def recall_fields(record: dict[str, Any]) -> dict[str, str]:
    data = _data(record)
    return {
        "source_id": str(record.get("source_id", "")),
        "recall_number": _first(data, "RecallNumber", "recall_number", "field_recall_number", "RECORD_ID", "recall_id") or str(record.get("record_id", "")),
        "date": _first(data, "RecallDate", "recall_date", "report_date", "recall_initiation_date", "field_recall_date", "RCDATE", "date") or str(record.get("record_date", "")),
        "title": _first(data, "Title", "title", "product_description", "field_title", "MFGNAME", "product"),
        "description": _first(data, "Description", "description", "reason_for_recall", "field_summary", "DESC_DEFECT"),
        "brand": _first(data, "Brand", "brand", "manufacturer", "MFGNAME", "recalling_firm"),
        "model": _first(data, "Model", "model", "model_number", "model_numbers", "product_model"),
        "barcode": _first(data, "UPC", "upc", "barcode", "gtin", "product_upc"),
        "official_url": _first(data, "RecallURL", "recall_url", "URL", "url", "link", "web_url", "source_url") or str(record.get("source_url", "")),
        "fetched_at": str(record.get("fetched_at", "")),
    }


def match_item(item: dict[str, Any], recalls: list[dict[str, Any]], *, as_of: str | None = None) -> dict[str, Any]:
    """Match identifiers first; send fuzzy/underspecified cases to human review."""
    as_of = as_of or date.today().isoformat()
    barcode = _norm(item.get("barcode") or item.get("upc") or item.get("gtin"))
    model = _norm(item.get("model") or item.get("model_number"))
    brand = _norm(item.get("brand") or item.get("manufacturer"))
    if not barcode and not model and not brand:
        return {"result": "uncertain — please check", "checked_at": as_of, "ruleset": MATCH_RULESET, "recalls": [], "detail": "Provide a barcode, model or brand to check."}

    exact: list[dict[str, str]] = []
    borderline = False
    for row in recalls:
        fields = recall_fields(row)
        blob = _norm(" ".join((fields["title"], fields["description"], fields["brand"], fields["model"], fields["barcode"])))
        row_barcode = _norm(fields["barcode"])
        row_model = _norm(fields["model"])
        row_brand = _norm(fields["brand"])
        barcode_match = bool(barcode and (barcode == row_barcode or barcode in blob))
        model_match = bool(model and (model == row_model or (len(model) >= 4 and model in blob)))
        brand_match = bool(brand and (brand == row_brand or (len(brand) >= 4 and brand in blob)))
        if barcode_match or (model_match and (not brand or brand_match)):
            exact.append(fields)
            continue
        if model and brand:
            model_ratio = difflib.SequenceMatcher(None, model, row_model or blob).ratio()
            brand_ratio = difflib.SequenceMatcher(None, brand, row_brand or blob).ratio()
            if model_ratio >= 0.72 and brand_ratio >= 0.72:
                borderline = True
    if exact:
        result = "match"
    elif borderline or not recalls:
        result = "uncertain — please check"
    else:
        result = f"no match found in {SOURCE_LABELS} as of {as_of}"
    return {
        "result": result,
        "checked_at": as_of,
        "ruleset": MATCH_RULESET,
        "recalls": [{"source_id": row["source_id"], "recall_number": row["recall_number"], "date": row["date"], "title": row["title"], "official_url": row["official_url"]} for row in exact],
        "detail": "Exact barcode or model match." if exact else ("A similar brand/model needs review." if borderline else "No matching record in the available feed snapshot."),
    }


def query_recall_feeds(*, feed_query=query_feed) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    for source_id in SOURCES:
        source_rows = feed_query(source_id)
        if not source_rows:
            missing.append(source_id)
        rows.extend(source_rows)
    return rows, missing


def check_item(item: dict[str, Any], *, feed_query=query_feed, as_of: str | None = None) -> dict[str, Any]:
    rows, missing = query_recall_feeds(feed_query=feed_query)
    if missing:
        return {"result": "uncertain — please check", "checked_at": as_of or date.today().isoformat(), "ruleset": MATCH_RULESET, "recalls": [], "detail": "Recall feed snapshots unavailable: " + ", ".join(missing)}
    fetched = [row.get("fetched_at", "") for row in rows if row.get("fetched_at")]
    try:
        latest = max(datetime.fromisoformat(value.replace("Z", "+00:00")) for value in fetched)
        if (datetime.now(timezone.utc) - latest).total_seconds() > 48 * 60 * 60:
            return {"result": "uncertain — please check", "checked_at": as_of or date.today().isoformat(), "ruleset": MATCH_RULESET, "recalls": [], "detail": "Recall feed data is more than 48 hours old."}
    except (ValueError, TypeError):
        return {"result": "uncertain — please check", "checked_at": as_of or date.today().isoformat(), "ruleset": MATCH_RULESET, "recalls": [], "detail": "Recall feed freshness could not be verified."}
    return match_item(item, rows, as_of=as_of)


def process_csv(source: str | Path, destination: str | Path, recalls: list[dict[str, Any]], *, as_of: str | None = None) -> Path:
    source, destination = Path(source), Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open(newline="", encoding="utf-8-sig") as src:
        reader = csv.DictReader(src)
        fields = list(reader.fieldnames or [])
        out_fields = fields + ["recall_result", "recall_numbers", "official_links", "checked_at"]
        with destination.open("w", newline="", encoding="utf-8") as dst:
            writer = csv.DictWriter(dst, fieldnames=out_fields)
            writer.writeheader()
            for row in reader:
                result = match_item(row, recalls, as_of=as_of)
                row.update({"recall_result": result["result"], "recall_numbers": ",".join(hit["recall_number"] for hit in result["recalls"]), "official_links": " ".join(hit["official_url"] for hit in result["recalls"]), "checked_at": result["checked_at"]})
                writer.writerow(row)
    return destination


def generate_pages(recalls: list[dict[str, Any]], directory: str | Path, *, limit: int | None = None) -> list[str]:
    """Write one escaped, source-linked local HTML page per distinct recall."""
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    pages: list[str] = []
    seen: set[tuple[str, str]] = set()
    for row in recalls:
        data = recall_fields(row)
        key = (data["source_id"], data["recall_number"])
        if key in seen:
            continue
        seen.add(key)
        if limit is not None and len(pages) >= limit:
            break
        slug = re.sub(r"[^a-zA-Z0-9-]+", "-", f"{data['source_id']}-{data['recall_number']}").strip("-").lower() or "recall"
        dest = root / f"{slug}.html"
        title = data["title"] or "Recall notice"
        url = data["official_url"] or row.get("source_url", "")
        if not str(url).startswith("https://"):
            url = str(row.get("source_url", ""))
        body = f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{html.escape(title)} — recall {html.escape(data['recall_number'])}</title><main><p>Recall checker</p><h1>{html.escape(title)}</h1><dl><dt>Recall number</dt><dd>{html.escape(data['recall_number'])}</dd><dt>Recall date</dt><dd>{html.escape(data['date'])}</dd><dt>Source</dt><dd>{html.escape(data['source_id'])}</dd></dl><p>{html.escape(data['description'])}</p><p><a href="{html.escape(url, quote=True)}" rel="noopener noreferrer">View the official recall notice</a></p></main></html>"""
        dest.write_text(body, encoding="utf-8")
        pages.append(str(dest))
    return pages


def api_match_payload(body: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(body, dict):
        raise ValueError("request body must be a JSON object")
    item = body.get("item", body)
    if not isinstance(item, dict):
        raise ValueError("item must be a JSON object")
    return check_item(item)
