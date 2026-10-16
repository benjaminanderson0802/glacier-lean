"""Keyless official recall-source clients and record normalization."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)
TIMEOUT_SECONDS = 12
RETRIES = 2
RATE_INTERVAL_SECONDS = 0.2
_rate_lock = threading.Lock()
_last_request = 0.0
HEADERS = {"User-Agent": "ProductRecallChecker/0.1 (public-data lookup; contact via Actor issues)", "Accept": "application/json"}
SOURCE_URLS = {
    "CPSC": "https://www.saferproducts.gov/RestWebServices/Recall",
    "NHTSA": "https://api.nhtsa.gov/recalls/recallsByVehicle",
    "FDA-food": "https://api.fda.gov/food/enforcement.json",
    "FDA-drug": "https://api.fda.gov/drug/enforcement.json",
    "FDA-device": "https://api.fda.gov/device/enforcement.json",
}


class SourceUnavailable(RuntimeError):
    pass


def as_of() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _polite_wait() -> None:
    global _last_request
    with _rate_lock:
        delay = RATE_INTERVAL_SECONDS - (time.monotonic() - _last_request)
        if delay > 0:
            time.sleep(delay)
        _last_request = time.monotonic()


def request_json(url: str, params: Mapping[str, Any] | None = None) -> Any:
    last_error: Exception | None = None
    for attempt in range(RETRIES + 1):
        try:
            _polite_wait()
            started = time.monotonic()
            response = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT_SECONDS)
            if url == SOURCE_URLS["CPSC"] and os.getenv("RECALL_DIAGNOSTICS") == "1":
                logger.info(
                    "Recall diagnostic HTTP source=CPSC url=%s status=%d content_type=%s bytes=%d elapsed_ms=%d",
                    url,
                    response.status_code,
                    response.headers.get("content-type", ""),
                    len(response.content),
                    round((time.monotonic() - started) * 1000),
                )
            # openFDA uses HTTP 404 with a source-specific code for valid empty searches.
            if response.status_code == 404 and "api.fda.gov" in url:
                try:
                    payload = response.json()
                except ValueError:
                    response.raise_for_status()
                if payload.get("error", {}).get("code") in {"NO_RECORDS_FOUND", "NOT_FOUND"}:
                    return {"results": [], "meta": {"no_records": True}}
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt < RETRIES:
                time.sleep(0.35 * (attempt + 1))
    raise SourceUnavailable(str(last_error or "source request failed"))


def _first(record: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return ""


def _record(source: str, record: Mapping[str, Any], *, fda_kind: str = "") -> dict[str, Any]:
    if source == "CPSC":
        products = record.get("Products") or []
        if isinstance(products, Mapping):
            products = products.get("Product") or []
        if isinstance(products, Mapping):
            products = [products]
        product_rows = [item for item in products if isinstance(item, Mapping)] if isinstance(products, list) else []
        product_names = " ".join(str(_first(item, "Name", "ProductName")) for item in product_rows)
        product_descriptions = " ".join(str(_first(item, "Description")) for item in product_rows)
        product_models = " ".join(str(_first(item, "Model", "ProductModel")) for item in product_rows)
        product_upcs = record.get("ProductUPCs") or []
        if isinstance(product_upcs, Mapping):
            product_upcs = product_upcs.get("ProductUPC") or []
        if isinstance(product_upcs, Mapping):
            product_upcs = [product_upcs]
        nested_upcs = [str(_first(item, "UPC")) for item in product_upcs if isinstance(item, Mapping)] if isinstance(product_upcs, list) else []
        upcs = _first(record, "UPC", "ProductUPC")
        if not upcs:
            upcs = nested_upcs
        manufacturers = record.get("Manufacturers") or []
        if isinstance(manufacturers, Mapping):
            manufacturers = manufacturers.get("Manufacturer") or []
        if isinstance(manufacturers, Mapping):
            manufacturers = [manufacturers]
        manufacturer_names = " ".join(str(_first(item, "Name")) for item in manufacturers if isinstance(item, Mapping)) if isinstance(manufacturers, list) else ""
        hazards = record.get("Hazards") or []
        if isinstance(hazards, Mapping):
            hazards = hazards.get("Hazard") or []
        if isinstance(hazards, Mapping):
            hazards = [hazards]
        hazard_names = " ".join(str(_first(item, "Name")) for item in hazards if isinstance(item, Mapping)) if isinstance(hazards, list) else ""
        remedies = record.get("Remedies") or []
        if isinstance(remedies, Mapping):
            remedies = remedies.get("Remedy") or []
        if isinstance(remedies, Mapping):
            remedies = [remedies]
        remedy_names = " ".join(str(_first(item, "Name")) for item in remedies if isinstance(item, Mapping)) if isinstance(remedies, list) else ""
        title = _first(record, "Title", "RecallTitle", "ProductName")
        description = _first(record, "Description", "RecallDescription", "ProductDescription")
        return {
            "source": source,
            "recall_id": str(_first(record, "RecallNumber", "RecallID", "RecallId")),
            "title": str(title),
            "date": str(_first(record, "RecallDate")),
            "hazard": str(_first(record, "Hazard", "Injury") or hazard_names),
            "remedy": str(_first(record, "Remedy", "RemedyOption") or remedy_names),
            "url": str(_first(record, "URL", "RecallURL")),
            "barcode_values": [str(v).strip() for v in (upcs if isinstance(upcs, list) else str(upcs).replace(";", "|").split("|")) if str(v).strip()],
            "brand": str(_first(record, "Manufacturer", "Company") or manufacturer_names),
            "model": str(_first(record, "Model", "ProductModel") or product_models),
            "description": f"{description} {product_names} {product_descriptions} {product_models}".strip(),
        }
    if source == "NHTSA":
        title = f"{_first(record, 'Make')} {_first(record, 'Model')} vehicle recall".strip()
        recall_id = str(_first(record, "NHTSACampaignNumber", "CampaignNumber"))
        return {
            "source": source,
            "recall_id": recall_id,
            "title": title,
            "date": str(_first(record, "ReportReceivedDate", "RecallDate")),
            "hazard": str(_first(record, "Consequence", "Summary")),
            "remedy": str(_first(record, "Remedy")),
            "url": f"https://www.nhtsa.gov/recalls?nhtsaId={quote(recall_id)}",
            "barcode_values": [],
            "brand": str(_first(record, "Make")),
            "model": str(_first(record, "Model")),
            "description": f"{_first(record, 'Summary')} {_first(record, 'Component')} {record.get('ModelYear', '')}".strip(),
        }
    title = str(_first(record, "product_description", "product_description_text"))
    recall_id = str(_first(record, "recall_number", "event_id"))
    openfda = record.get("openfda") or {}
    if not isinstance(openfda, Mapping):
        openfda = {}
    upcs = openfda.get("upc") or []
    if isinstance(upcs, str):
        upcs = [upcs]
    brand_values = openfda.get("brand_name") or []
    if isinstance(brand_values, str):
        brand_values = [brand_values]
    kind = fda_kind or source.removeprefix("FDA-")
    return {
        "source": f"FDA ({kind})",
        "recall_id": recall_id,
        "title": title,
        "date": str(_first(record, "recall_initiation_date", "report_date")),
        "hazard": str(_first(record, "reason_for_recall", "classification")),
        "remedy": str(_first(record, "more_code_info", "distribution_pattern")),
        "url": f"{SOURCE_URLS[f'FDA-{kind}']}?search=recall_number%3A%22{quote(recall_id)}%22" if recall_id else SOURCE_URLS[f"FDA-{kind}"],
        "barcode_values": [str(value) for value in upcs],
        "brand": " ".join(str(value) for value in brand_values) or str(_first(record, "recalling_firm")),
        "model": "",
        "description": f"{title} {record.get('reason_for_recall', '')} {record.get('recalling_firm', '')}".strip(),
    }


def normalize_cpsc(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        raise SourceUnavailable("CPSC returned an unexpected response")
    return [_record("CPSC", item) for item in payload if isinstance(item, Mapping)]


def normalize_nhtsa(payload: Any) -> list[dict[str, Any]]:
    results = payload.get("results") if isinstance(payload, Mapping) else None
    if not isinstance(results, list):
        raise SourceUnavailable("NHTSA returned an unexpected response")
    return [_record("NHTSA", item) for item in results if isinstance(item, Mapping)]


def normalize_fda(payload: Any, kind: str) -> list[dict[str, Any]]:
    results = payload.get("results", []) if isinstance(payload, Mapping) else None
    if not isinstance(results, list):
        raise SourceUnavailable(f"FDA {kind} returned an unexpected response")
    return [_record(f"FDA-{kind}", item, fda_kind=kind) for item in results if isinstance(item, Mapping)]


def _fda_search(query: Mapping[str, Any], kind: str) -> str | None:
    barcode = "".join(ch for ch in str(query.get("barcode", "")) if ch.isdigit())
    if barcode:
        return f'openfda.upc:"{barcode}"'
    name = query.get("product_name") or query.get("model") or query.get("brand")
    if not name:
        return None
    field = "product_description"
    # Quote and escape user text so query parameters cannot alter the field syntax.
    safe = str(name).replace("\\", " ").replace('"', " ").strip()
    return f'{field}:"{safe}"'


_CPSC_GENERIC_TRAILING_WORDS = {"seat", "sleeper", "toy"}


def _cpsc_searches(query: Mapping[str, Any]) -> list[dict[str, str]]:
    """Build no more than six independent CPSC searches without ANDing fields."""
    if query.get("barcode"):
        return [{"format": "json", "UPC": str(query["barcode"])}]

    phrase = str(query.get("product_name") or query.get("model") or "").strip()
    if not phrase:
        return []

    words = phrase.split()
    phrases = [phrase]
    shortened = words[:]
    while len(shortened) > 2 and shortened[-1].strip(".,;:()[]{}").casefold() in _CPSC_GENERIC_TRAILING_WORDS:
        shortened.pop()
        candidate = " ".join(shortened)
        if candidate not in phrases:
            phrases.append(candidate)

    # CPSC's text search is literal about apostrophes. Keep the probes
    # independent and representative: full product name, shortened recall
    # title, then a shortened ProductName apostrophe variant.
    # FDA also checks three separate endpoints for each name-only lookup, so
    # limiting this plan to three requests keeps the whole lookup at six.
    shortest = phrases[-1]
    without_apostrophes = shortest.replace("'", "").replace("’", "")
    apostrophe_variant = without_apostrophes
    if apostrophe_variant == shortest:
        apostrophe_variant = shortest.replace(" n ", " 'n ").replace(" N ", " 'N ")
    candidates = [
        ("ProductName", phrase),
        ("RecallTitle", shortest),
        ("ProductName", apostrophe_variant),
    ]
    searches: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for field, candidate in candidates:
        key = (field, candidate)
        if candidate and key not in seen:
            searches.append({"format": "json", field: candidate})
            seen.add(key)
    return searches


def _dedupe_cpsc(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Union CPSC search results by official recall ID, retaining id-less rows."""
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in records:
        recall_id = str(record.get("recall_id") or "").strip()
        if recall_id and recall_id in seen:
            continue
        if recall_id:
            seen.add(recall_id)
        deduped.append(record)
    return deduped


def check_sources(query: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, dict[str, str]]]:
    recalls: list[dict[str, Any]] = []
    statuses: dict[str, dict[str, str]] = {}

    cpsc_searches = _cpsc_searches(query)
    cpsc_records: list[dict[str, Any]] = []
    cpsc_errors: list[str] = []
    for params in cpsc_searches:
        try:
            payload = request_json(SOURCE_URLS["CPSC"], params)
            normalized = normalize_cpsc(payload)
            cpsc_records.extend(normalized)
            if os.getenv("RECALL_DIAGNOSTICS") == "1":
                field = next((name for name in params if name != "format"), "unknown")
                phrase = str(params.get(field, ""))
                is_known_canary = (
                    query.get("brand") == "Fisher-Price"
                    and query.get("product_name") == "Rock 'n Play Sleeper"
                )
                phrase_label = repr(phrase) if is_known_canary else f"<redacted:{len(phrase)} chars>"
                raw_count = len(payload) if isinstance(payload, list) else -1
                logger.info(
                    "Recall diagnostic CPSC probe field=%s phrase=%s raw_rows=%d normalized_rows=%d",
                    field,
                    phrase_label,
                    raw_count,
                    len(normalized),
                )
        except (SourceUnavailable, requests.RequestException, ValueError) as exc:
            cpsc_errors.append(str(exc)[:240])
    recalls.extend(_dedupe_cpsc(cpsc_records))
    if not cpsc_searches:
        statuses["CPSC"] = {"status": "skipped", "as_of": as_of(), "message": "No UPC or product phrase was provided."}
    elif cpsc_errors:
        failure_count = len(cpsc_errors)
        search_count = len(cpsc_searches)
        if failure_count == search_count:
            message = cpsc_errors[-1]
        else:
            details = "; ".join(cpsc_errors)
            message = f"{failure_count} of {search_count} CPSC searches failed: {details}"
        statuses["CPSC"] = {"status": "error", "as_of": as_of(), "message": message[:240]}
    else:
        statuses["CPSC"] = {"status": "ok", "as_of": as_of()}

    if query.get("brand") and query.get("model") and query.get("year"):
        try:
            params = {"make": str(query["brand"]), "model": str(query["model"]), "modelYear": str(query["year"]) }
            recalls.extend(normalize_nhtsa(request_json(SOURCE_URLS["NHTSA"], params)))
            statuses["NHTSA"] = {"status": "ok", "as_of": as_of()}
        except (SourceUnavailable, requests.RequestException, ValueError) as exc:
            statuses["NHTSA"] = {"status": "error", "as_of": as_of(), "message": str(exc)[:240]}
    else:
        statuses["NHTSA"] = {"status": "skipped", "as_of": as_of(), "message": "Vehicle make, model and year are required by this source."}

    for kind in ("food", "drug", "device"):
        source_name = f"FDA-{kind}"
        search = _fda_search(query, kind)
        if not search:
            statuses[source_name] = {"status": "skipped", "as_of": as_of(), "message": "No supported search identifier was provided."}
            continue
        try:
            payload = request_json(SOURCE_URLS[source_name], {"search": search, "limit": "100"})
            recalls.extend(normalize_fda(payload, kind))
            statuses[source_name] = {"status": "ok", "as_of": as_of()}
        except (SourceUnavailable, requests.RequestException, ValueError) as exc:
            statuses[source_name] = {"status": "error", "as_of": as_of(), "message": str(exc)[:240]}
    return recalls, statuses
