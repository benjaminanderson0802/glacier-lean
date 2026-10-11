"""Prepare a reviewed DIBBS bid sheet from public solicitations and owner-supplied quotes."""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
from urllib.parse import urlencode, urlparse
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


FEED_SOURCE = "dla_dibbs"
SAM_SEARCH_URL = "https://api.sam.gov/opportunities/v2/search"
SAM_NAICS = ("423840", "423830", "423710", "423610", "423120")
SAM_PAGE_SIZE = 100
SAM_MAX_PAGES_PER_NAICS = 5
ALLOWED_SUPPLIER_TYPES = {"manufacturer", "authorized_distributor"}
QUOTE_FIELD_VALUES = {
    "solicitation_number": ("solicitation_number", "solicitation_number"),
    "nsn": ("solicitation", "nsn"),
    "part_number": ("quote", "part_number"),
    "quantity": ("solicitation", "quantity"),
    "unit_price": ("quote", "unit_bid_price"),
    "unit_bid_price": ("quote", "unit_bid_price"),
    "supplier_name": ("quote", "supplier_name"),
}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sam_api_key() -> str:
    """Read the owner's key from Glacier's OS keychain, never from a file or CLI arg."""
    backend = str(Path(__file__).resolve().parents[3] / "glacier" / "backend")
    if backend not in os.sys.path:
        os.sys.path.insert(0, backend)
    try:
        import secrets_store  # type: ignore[import-not-found]
        key = secrets_store.resolve("{secret:sam_api_key}")
    except (ValueError, ImportError, RuntimeError):
        key = None
    if not key:
        raise ValueError("SAM.gov is not configured. Add sam_api_key in Glacier Settings > Secrets.")
    return str(key)


def _sam_request(params: dict[str, Any], api_key: str) -> dict[str, Any]:
    query = urlencode({**params, "api_key": api_key}, doseq=True)
    request = Request(SAM_SEARCH_URL + "?" + query, headers={"Accept": "application/json", "User-Agent": "Glacier DIBBS venture"})
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        # Do not include the request URL: SAM.gov receives the key as a query parameter.
        raise ValueError(f"SAM.gov opportunities API returned HTTP {exc.code}.") from None
    except (URLError, TimeoutError, json.JSONDecodeError):
        raise ValueError("Could not read a valid response from the SAM.gov opportunities API.") from None
    if not isinstance(payload, dict) or not isinstance(payload.get("opportunitiesData"), list):
        raise ValueError("SAM.gov returned an unexpected opportunities response format.")
    return payload


def _is_dla(row: dict[str, Any]) -> bool:
    def names_dla(value: Any) -> bool:
        normalized = re.sub(r"[^A-Z0-9]+", " ", str(value or "").upper())
        return "DEFENSE LOGISTICS AGENCY" in normalized or bool(re.search(r"\bDLA\b", normalized))

    department = str(row.get("department") or "").strip()
    sub_tier = str(row.get("subTier") or "").strip()
    office = str(row.get("office") or "").strip()
    parent_path = str(row.get("fullParentPathName") or "").strip()
    if department and not names_dla(department):
        normalized_department = re.sub(r"[^A-Z0-9]+", " ", department.upper()).strip()
        if normalized_department not in {"DEPARTMENT OF DEFENSE", "DEPT OF DEFENSE", "DEFENSE"}:
            return False
    if sub_tier and not names_dla(sub_tier):
        return False
    if office and not names_dla(office):
        return False
    if parent_path:
        return names_dla(parent_path)
    return names_dla(department) or names_dla(sub_tier) or names_dla(office)


def _sam_opportunities(payloads: list[dict[str, Any]], *, as_of: date,
                       naics_codes: set[str] | tuple[str, ...] = SAM_NAICS) -> list[dict[str, Any]]:
    """Normalize official v2 response rows, retaining source facts and ranking likely open notices."""
    rows_by_id: dict[str, dict[str, Any]] = {}
    for payload in payloads:
        for raw in payload.get("opportunitiesData", []):
            if not isinstance(raw, dict) or not _is_dla(raw):
                continue
            naics = str(raw.get("naicsCode") or "").strip()
            if naics not in naics_codes:
                continue
            notice_id = str(raw.get("noticeId") or "").strip()
            solnum = str(raw.get("solicitationNumber") or "").strip()
            key = notice_id or solnum
            if not key:
                continue
            deadline_raw = str(raw.get("responseDeadLine") or "").strip()
            deadline = None
            if deadline_raw and deadline_raw.lower() != "null":
                try:
                    deadline = date.fromisoformat(deadline_raw[:10])
                except ValueError:
                    deadline = None
            active = str(raw.get("active") or "").strip().lower() == "yes"
            current = deadline is not None and deadline >= as_of
            sam_url = str(raw.get("uiLink") or "").strip()
            if sam_url.lower() in {"", "null"} or urlparse(sam_url).hostname not in {"sam.gov", "www.sam.gov"}:
                sam_url = ""
            owner_review_url = "https://sam.gov/search/?" + urlencode({"index": "opp", "keywords": solnum or notice_id})
            score = (100 if active else 0) + (50 if current else 0) + (25 if str(raw.get("type") or "").lower() in {"solicitation", "combined synopsis/solicitation"} else 0)
            rows_by_id[key] = {
                "notice_id": notice_id,
                "solicitation_number": solnum,
                "title": str(raw.get("title") or "").strip(),
                "department": str(raw.get("department") or "").strip(),
                "sub_tier": str(raw.get("subTier") or "").strip(),
                "office": str(raw.get("office") or "").strip(),
                "organization_path": str(raw.get("fullParentPathName") or "").strip(),
                "naics_code": naics,
                "type": str(raw.get("type") or "").strip(),
                "posted_date": str(raw.get("postedDate") or "").strip(),
                "response_deadline": deadline.isoformat() if deadline else None,
                "active": active,
                "source_url": sam_url,
                "owner_review_url": owner_review_url,
                "rank_score": score,
                "rank_reasons": [reason for condition, reason in ((active, "SAM marks this notice active"), (current, "response deadline has not passed"), (str(raw.get("type") or "").lower() in {"solicitation", "combined synopsis/solicitation"}, "notice type is a solicitation")) if condition],
                "owner_review_required": True,
                "discovery_only": True,
            }
    return sorted(rows_by_id.values(), key=lambda row: (
        -row["rank_score"],
        row["response_deadline"] or "9999-12-31",
        row["posted_date"],
        row["solicitation_number"],
    ))


def parse_sam_opportunities(payload: dict[str, Any], *, naics_codes: set[str] | tuple[str, ...] = SAM_NAICS,
                            as_of: date | None = None) -> list[dict[str, Any]]:
    """Parse and rank one SAM.gov v2 response envelope for owner review.

    The function deliberately accepts only the public API's ``opportunitiesData``
    envelope and produces discovery candidates; it does not visit DIBBS or
    acknowledge any consent page.
    """
    if not isinstance(payload, dict) or not isinstance(payload.get("opportunitiesData"), list):
        raise ValueError("SAM.gov returned an unexpected opportunities response format.")
    today = as_of or datetime.now(timezone.utc).date()
    return _sam_opportunities([payload], as_of=today, naics_codes=naics_codes)


def fetch_sam_opportunities(*, api_key: str | None = None, as_of: date | None = None,
                            request_json: Any = _sam_request) -> dict[str, Any]:
    """Read active DLA contract notices for the venture's NAICS list using public API v2."""
    key = api_key or _sam_api_key()
    today = as_of or datetime.now(timezone.utc).date()
    posted_from = date(today.year - 1, today.month, min(today.day, 28))
    posted_to = today
    payloads = []
    alerts = []
    for naics in SAM_NAICS:
        total_for_naics = 0
        for page in range(SAM_MAX_PAGES_PER_NAICS):
            offset = page * SAM_PAGE_SIZE
            payload = request_json({
                "organizationName": "DLA",
                "ncode": naics,
                "ptype": ["o", "k"],
                "postedFrom": posted_from.strftime("%m/%d/%Y"),
                "postedTo": posted_to.strftime("%m/%d/%Y"),
                "limit": SAM_PAGE_SIZE,
                "offset": offset,
            }, key)
            payloads.append(payload)
            total = int(payload.get("totalRecords") or 0)
            total_for_naics = max(total_for_naics, total)
            if offset + SAM_PAGE_SIZE >= total or not payload["opportunitiesData"]:
                break
        if total_for_naics > SAM_PAGE_SIZE * SAM_MAX_PAGES_PER_NAICS:
            alerts.append(f"SAM.gov has more than {SAM_PAGE_SIZE * SAM_MAX_PAGES_PER_NAICS} results for NAICS {naics}; candidate list is capped and incomplete.")
    opportunities = _sam_opportunities(payloads, as_of=today)
    return {
        "source": "SAM.gov Contract Opportunities API v2",
        "endpoint": SAM_SEARCH_URL,
        "as_of": today.isoformat(),
        "naics_codes": list(SAM_NAICS),
        "organization_filter": "DLA (verified locally against returned department/organization fields)",
        "pages_read": len(payloads),
        "ranked_opportunities": opportunities,
        "rows": len(opportunities),
        "alerts": alerts,
        "live_source_checked": True,
        "owner_review_required": True,
        "discovery_only": True,
    }


def _money(value: Any, label: str) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{label} must be a decimal amount") from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError(f"{label} must be a finite, non-negative amount")
    return amount


def _safe_filename(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    name = Path(value.strip()).name
    if name != value.strip() or name in {".", ".."} or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}\.csv", name, re.I):
        return None
    return name


def _evidence_on_file(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    path = Path(value.strip())
    if not path.is_absolute():
        path = Path(os.environ.get("GLACIER_HOME", ".")) / "ventures" / "dibbs-supply" / "incoming" / path
    return path.is_file()


def _quote_value(field: str, solicitation: dict[str, Any], quote: dict[str, Any]) -> Any:
    source, key = QUOTE_FIELD_VALUES[field]
    if field == "solicitation_number":
        return solicitation.get(key)
    return (solicitation if source == "solicitation" else quote).get(key)


def _find_quote(solicitation: dict[str, Any], quotes: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [quote for quote in quotes if str(quote.get("solicitation_number", "")).strip() == str(solicitation.get("solicitation_number", "")).strip()]
    # A part mismatch is never repaired by choosing a supplier quote for another part.
    exact = [quote for quote in candidates if str(quote.get("part_number", "")).strip() == str(solicitation.get("part_number", "")).strip()]
    return exact[0] if len(exact) == 1 else None


def prepare_bids(solicitations_path: Path, quotes_path: Path, output_dir: Path, *, as_of: date | None = None) -> dict[str, Any]:
    """Validate quote and solicitation facts, then write only fully matched CSV quote batches."""
    solicitations = _read_json(Path(solicitations_path))
    quotes = _read_json(Path(quotes_path))
    if not isinstance(solicitations, list) or not isinstance(quotes, list):
        raise ValueError("solicitations and quotes inputs must each be JSON arrays")
    if not all(isinstance(row, dict) for row in [*solicitations, *quotes]):
        raise ValueError("solicitations and quotes inputs must contain JSON objects")

    today = as_of or datetime.now(timezone.utc).date()
    accepted: list[dict[str, Any]] = []
    uncertain: list[dict[str, Any]] = []
    quote_requests: list[dict[str, Any]] = []
    quote_request_uncertain: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    output_rows: dict[str, list[dict[str, Any]]] = {}
    for solicitation in solicitations:
        number = str(solicitation.get("solicitation_number", "")).strip()
        for source in solicitation.get("quote_sources", []) if isinstance(solicitation.get("quote_sources", []), list) else []:
            request_issues = []
            supplier_name = str(source.get("supplier_name", "")).strip() if isinstance(source, dict) else ""
            supplier_type = source.get("supplier_type") if isinstance(source, dict) else None
            contact_email = str(source.get("contact_email", "")).strip() if isinstance(source, dict) else ""
            contact_url = str(source.get("contact_url", "")).strip() if isinstance(source, dict) else ""
            business_name = str(solicitation.get("business_name", "")).strip()
            request_due = str(solicitation.get("supplier_quote_due_date", "")).strip()
            if solicitation.get("open_to_all_suppliers") is not True:
                request_issues.append("solicitation eligibility for all suppliers is not confirmed")
            if solicitation.get("electronic_part") is not False:
                request_issues.append("solicitation is not confirmed as non-electronic")
            try:
                solicitation_due = date.fromisoformat(str(solicitation.get("return_by_date", "")))
                if solicitation_due < today:
                    request_issues.append("solicitation return date has passed")
            except ValueError:
                request_issues.append("solicitation return-by date is missing or invalid")
            if supplier_type not in ALLOWED_SUPPLIER_TYPES:
                request_issues.append("supplier is not identified as the original manufacturer or an authorized distributor")
            if not supplier_name or not business_name:
                request_issues.append("supplier or sending business name is missing")
            if bool(contact_email) == bool(contact_url):
                request_issues.append("provide exactly one owner-verified supplier email or HTTPS contact URL")
            elif contact_email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", contact_email):
                request_issues.append("supplier email address is invalid")
            elif contact_url and (urlparse(contact_url).scheme != "https" or not urlparse(contact_url).netloc):
                request_issues.append("supplier contact URL must use HTTPS")
            try:
                due_date = date.fromisoformat(request_due)
                if due_date < today:
                    request_issues.append("supplier quote request due date has passed")
            except ValueError:
                due_date = None
                request_issues.append("supplier quote request due date is missing or invalid")
            source_url = str(solicitation.get("source_url", "")).strip()
            source_parts = urlparse(source_url)
            if source_parts.scheme != "https" or source_parts.hostname not in {"dibbs.bsm.dla.mil", "www.dibbs.bsm.dla.mil"}:
                request_issues.append("official DIBBS solicitation link is missing or invalid")
            if not solicitation.get("part_number") or not solicitation.get("nsn") or not solicitation.get("quantity"):
                request_issues.append("exact part number, NSN, or quantity is missing")
            if not _evidence_on_file(source.get("authorization_evidence") if isinstance(source, dict) else None):
                request_issues.append("supplier authorization evidence is not on file")
            if request_issues:
                quote_request_uncertain.append({"solicitation_number": number, "supplier_name": supplier_name, "result": "uncertain — please check", "reasons": request_issues})
            else:
                contact = contact_email or contact_url
                quote_requests.append({
                    "solicitation_number": number,
                    "supplier_name": supplier_name,
                    "supplier_type": supplier_type,
                    "to": contact,
                    "subject": f"Quote request — DLA DIBBS solicitation {number} — part {solicitation['part_number']}",
                    "body": (f"Hello {supplier_name},\n\n{business_name} requests a quote for DLA DIBBS solicitation {number}. "
                             f"Please quote exact part number {solicitation['part_number']} (NSN {solicitation['nsn']}) "
                             f"for quantity {solicitation['quantity']} by {due_date.isoformat()}. Include unit price, available quantity, "
                             "lead time, quote validity, shipping, manufacturer/authorized-distributor status, and traceability documentation availability. "
                             f"Solicitation source: {source_url}\n\nRegards,\n{business_name}"),
                    "authorization_evidence": source["authorization_evidence"],
                    "sent": False,
                })
        issues: list[str] = []
        if not number:
            issues.append("solicitation number is missing")
        source_url = str(solicitation.get("source_url", "")).strip()
        source_parts = urlparse(source_url)
        if source_parts.scheme != "https" or source_parts.hostname not in {"dibbs.bsm.dla.mil", "www.dibbs.bsm.dla.mil"} or number.lower() not in source_url.lower():
            issues.append("official DIBBS solicitation link for this exact number is missing or invalid")
        if solicitation.get("open_to_all_suppliers") is False:
            excluded.append({"solicitation_number": number, "result": f"no match found in DLA DIBBS and supplier quotes as of {today.isoformat()}", "reason": "not open to all suppliers"})
            continue
        if solicitation.get("electronic_part") is True:
            excluded.append({"solicitation_number": number, "result": f"no match found in DLA DIBBS and supplier quotes as of {today.isoformat()}", "reason": "electronic parts are outside this venture"})
            continue
        if solicitation.get("open_to_all_suppliers") is not True:
            issues.append("supplier eligibility is not explicitly confirmed")
        if solicitation.get("electronic_part") is not False:
            issues.append("part type is not explicitly confirmed as non-electronic")
        if not solicitation.get("nsn") or not solicitation.get("part_number"):
            issues.append("NSN or exact part number is missing")
        try:
            due = date.fromisoformat(str(solicitation.get("return_by_date", "")))
            if due < today:
                excluded.append({"solicitation_number": number, "result": f"no match found in DLA DIBBS and supplier quotes as of {today.isoformat()}", "reason": "solicitation return date has passed"})
                continue
        except ValueError:
            issues.append("return-by date is missing or invalid")
        try:
            quantity = int(solicitation.get("quantity"))
            if quantity <= 0:
                raise ValueError
        except (ValueError, TypeError):
            quantity = 0
            issues.append("solicitation quantity is missing or invalid")

        quote = _find_quote(solicitation, quotes)
        if quote is None:
            issues.append("no quote exactly matches this solicitation and part number")
        else:
            if quote.get("supplier_type") not in ALLOWED_SUPPLIER_TYPES:
                issues.append("supplier is not identified as the original manufacturer or an authorized distributor")
            if not quote.get("supplier_name") or not _evidence_on_file(quote.get("authorization_evidence")):
                issues.append("supplier identity or on-file authorization evidence is missing")
            if not _evidence_on_file(quote.get("traceability_evidence")):
                issues.append("traceability evidence is not on file; shipping must remain blocked")
            try:
                if int(quote.get("quantity", 0)) < quantity:
                    issues.append("supplier quote quantity does not cover the solicitation quantity")
            except (ValueError, TypeError):
                issues.append("supplier quote quantity is missing or invalid")
            try:
                unit_cost = _money(quote.get("unit_cost"), "unit cost")
                unit_price = _money(quote.get("unit_bid_price"), "unit bid price")
                if unit_cost <= 0 or unit_price <= 0:
                    raise ValueError("unit cost and unit bid price must be greater than zero")
                margin = (unit_price - unit_cost) / unit_price * Decimal("100")
                if margin < 0:
                    issues.append("unit bid price is below unit cost")
            except ValueError as exc:
                unit_cost = unit_price = Decimal("0")
                margin = Decimal("0")
                issues.append(str(exc))

        required_fields = solicitation.get("required_fields")
        filename = _safe_filename(solicitation.get("quote_file"))
        if not isinstance(required_fields, list) or not required_fields or not all(isinstance(field, str) for field in required_fields):
            issues.append("solicitation-specific required quote fields are missing")
        elif any(field not in QUOTE_FIELD_VALUES for field in required_fields):
            issues.append("a required solicitation field has no verified data mapping")
        if not filename:
            issues.append("solicitation-specific CSV output filename is missing or unsafe")

        if issues:
            uncertain.append({"solicitation_number": number, "result": "uncertain — please check", "reasons": issues})
            continue

        row = {
            "solicitation_number": number,
            "nsn": solicitation["nsn"],
            "part_number": solicitation["part_number"],
            "supplier_name": quote["supplier_name"],
            "supplier_type": quote["supplier_type"],
            "quantity": quantity,
            "unit_cost": str(unit_cost),
            "unit_bid_price": str(unit_price),
            "extended_bid": str((unit_price * quantity).quantize(Decimal("0.01"))),
            "gross_margin_percent": float(margin.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "return_by_date": due.isoformat(),
            "source_url": solicitation.get("source_url", ""),
            "authorization_evidence": quote["authorization_evidence"],
            "traceability_evidence": quote["traceability_evidence"],
            "result": "match",
        }
        accepted.append(row)
        output_rows.setdefault(filename, []).append({field: _quote_value(field, solicitation, quote) for field in required_fields})

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "quote-request-drafts.json").write_text(json.dumps(quote_requests, indent=2, ensure_ascii=False), encoding="utf-8")
    for filename, rows in output_rows.items():
        with (output_dir / filename).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    accepted.sort(key=lambda row: (-row["gross_margin_percent"], row["return_by_date"], row["solicitation_number"]))
    status = "match" if accepted else "uncertain — please check" if uncertain or quote_request_uncertain else f"no match found in DLA DIBBS and supplier quotes as of {today.isoformat()}"
    result = {
        "result": status,
        "as_of": today.isoformat(),
        "ranked_bids": accepted,
        "uncertain": uncertain,
        "excluded": excluded,
        "quote_files": sorted(output_rows),
        "quote_requests": quote_requests,
        "quote_request_uncertain": quote_request_uncertain,
        "quote_requests_sent": False,
        "submitted": False,
        "owner_must_sign_and_submit": True,
    }
    return result


def prepare_from_feed(output_dir: Path, solicitations_path: Path, quotes_path: Path) -> dict[str, Any]:
    """Legacy DIBBS discovery helper retained for the existing fixture check."""
    from ventures.blocks.feeds import query, sync

    sync_result = sync(FEED_SOURCE)
    feed_rows = query(FEED_SOURCE)
    owner_rows = _read_json(solicitations_path)
    if not isinstance(owner_rows, list):
        raise ValueError("solicitations input must be a JSON array")
    public_by_number = {str(row.get("record_id", "")): row for row in feed_rows}
    merged = []
    for supplied in owner_rows:
        if not isinstance(supplied, dict):
            raise ValueError("solicitations input must contain JSON objects")
        public = public_by_number.get(str(supplied.get("solicitation_number", "")))
        row = dict(supplied)
        if public:
            row["source_url"] = public["data"].get("source_url") or public.get("source_url")
            row["public_description"] = public["data"].get("description", "")
        else:
            row["source_url"] = row.get("source_url", "")
        merged.append(row)
    temporary = Path(output_dir) / "solicitations-from-feed.json"
    temporary.parent.mkdir(parents=True, exist_ok=True)
    temporary.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    result = prepare_bids(temporary, quotes_path, Path(output_dir) / "quote-files")
    result["feed"] = sync_result
    result["feed_rows"] = len(feed_rows)
    result["feed_alerts"] = sync_result.get("alerts", [])
    if result["feed_alerts"]:
        result["result"] = "uncertain — please check"
    result["source_note"] = "DIBBS feed is public-link discovery only; detailed eligibility, quote instructions, and part data require owner review against the linked solicitation."
    (Path(output_dir) / "bid-sheet.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def prepare_from_sam(output_dir: Path, solicitations_path: Path, quotes_path: Path,
                     *, api_key: str | None = None, as_of: date | None = None,
                     opportunity_fetcher: Any = fetch_sam_opportunities) -> dict[str, Any]:
    """Discover DLA notices through SAM.gov, then prepare bids only from owner-entered DIBBS facts and quotes."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        feed = opportunity_fetcher(api_key=api_key, as_of=as_of)
    except (ValueError, OSError) as exc:
        feed = {
            "source": "SAM.gov Contract Opportunities API v2",
            "endpoint": SAM_SEARCH_URL,
            "as_of": (as_of or datetime.now(timezone.utc).date()).isoformat(),
            "naics_codes": list(SAM_NAICS),
            "ranked_opportunities": [],
            "rows": 0,
            "live_source_checked": False,
            "alerts": [str(exc)],
            "discovery_only": True,
        }
    feed.setdefault("alerts", [])
    (output_dir / "sam-opportunities.json").write_text(json.dumps(feed, indent=2, ensure_ascii=False), encoding="utf-8")
    result = prepare_bids(solicitations_path, quotes_path, output_dir / "quote-files", as_of=as_of)
    result["sam_feed"] = {
        key: feed[key] for key in ("source", "endpoint", "as_of", "naics_codes", "organization_filter", "pages_read", "rows", "live_source_checked", "alerts", "discovery_only") if key in feed
    }
    result["ranked_opportunities"] = feed.get("ranked_opportunities", [])
    result["feed_alerts"] = feed.get("alerts", [])
    result["source_note"] = (
        "SAM.gov is a discovery source only. Verify each notice on the official DIBBS solicitation page and enter the exact DIBBS detail URL, part, eligibility, due date, quantity, and required quote fields in solicitations.json. "
        "Bid sheets use only owner-entered supplier quotes; Glacier does not contact suppliers, sign, or submit bids."
    )
    if result["feed_alerts"]:
        result["result"] = "uncertain — please check"
    (output_dir / "bid-sheet.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare", help="prepare from local solicitation and supplier quote JSON")
    prepare.add_argument("--solicitations", type=Path, required=True)
    prepare.add_argument("--quotes", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    daily = sub.add_parser("daily", help="sync DLA opportunities from SAM.gov and prepare local quote drafts")
    daily.add_argument("--solicitations", type=Path, required=True)
    daily.add_argument("--quotes", type=Path, required=True)
    daily.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = prepare_bids(args.solicitations, args.quotes, args.output) if args.command == "prepare" else prepare_from_sam(args.output, args.solicitations, args.quotes)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result.get("ranked_bids") or result.get("quote_requests"):
        return 0
    return 1 if result["result"] == "uncertain — please check" else 2


if __name__ == "__main__":
    raise SystemExit(main())
