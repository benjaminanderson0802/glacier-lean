"""Prepare customer-reviewed freight claim packets without contacting carriers."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ventures.blocks.connectors.clients import ShipStationClient
from ventures.blocks.connectors.common import ConnectorError
from ventures.blocks.deadlines import add as add_deadline, due as due_deadlines
from ventures.blocks.filer import prepare as prepare_portal_draft
from ventures.blocks.reader import read_document
from csv_intake import parse_shipments_csv


SLUG = "freight-claims"
REQUIRED_DOCUMENTS = ("delivery_receipt", "photos", "commercial_invoice", "bill_of_lading")
_MONEY = Decimal("0.01")
MAX_TRACKING_LOOKUPS = 100


class FreightShipStationReader(ShipStationClient):
    """Venture-local read-only adapter for ShipStation's documented label tracking GET."""

    def get_tracking_for_label(self, label_id: str) -> dict[str, Any]:
        if not label_id.strip():
            raise ValueError("label_id is required")
        return self._get(f"/labels/{quote(label_id, safe='')}/track")


def _money(value: Any, field: str) -> Decimal:
    try:
        amount = Decimal(str(value)).quantize(_MONEY, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"{field} must be a valid amount") from None
    if not amount.is_finite() or amount < 0:
        raise ValueError(f"{field} must be a nonnegative amount")
    return amount


def _document_paths(documents: dict[str, Any]) -> tuple[dict[str, list[str]], list[str]]:
    normalized: dict[str, list[str]] = {}
    missing: list[str] = []
    for kind in REQUIRED_DOCUMENTS:
        paths = documents.get(kind, [])
        if isinstance(paths, (str, Path)):
            paths = [str(paths)]
        valid = [str(Path(path).expanduser().resolve()) for path in paths
                 if isinstance(path, (str, Path)) and Path(path).expanduser().is_file()]
        normalized[kind] = valid
        if not valid:
            missing.append(kind)
    return normalized, missing


def _read_evidence(documents: dict[str, list[str]]) -> list[dict[str, Any]]:
    """Read attached source files with the shared reader and preserve uncertainty."""
    schema = {"shipment_id": ["Shipment ID", "Tracking Number"],
              "invoice_number": ["Invoice Number", "Invoice #"],
              "invoice_total": ["Invoice Total", "Total"]}
    reads = []
    for kind, paths in documents.items():
        for path in paths:
            try:
                result = read_document(path, schema=schema)
                reads.append({
                    "kind": kind,
                    "path": path,
                    "fields": result.get("fields", {}),
                    "text_excerpt": str(result.get("text", ""))[:600],
                    "read_error": None,
                })
            except (OSError, RuntimeError, ValueError) as exc:
                reads.append({"kind": kind, "path": path, "fields": {},
                              "text_excerpt": "", "read_error": str(exc)[:240]})
    return reads


def build_claim_packet(claim: dict[str, Any], *, evidence_dir: str | Path | None = None,
                       read_sources: bool = True) -> dict[str, Any]:
    """Build a packet draft using only confirmed damaged-item invoice values.

    The return value contains a prefilled email draft only. It never sends a
    message, opens a carrier portal, or submits a claim.
    """
    shipment = claim.get("shipment") or {}
    shipment_id = str(shipment.get("shipment_id", "")).strip()
    if not shipment_id:
        raise ValueError("shipment.shipment_id is required")
    tracking_number = str(shipment.get("tracking_number", "")).strip()
    carrier_email = str(claim.get("carrier_claim_email", "")).strip()
    if any(ord(char) < 32 for char in shipment_id + tracking_number):
        raise ValueError("shipment identifiers cannot contain control characters")
    email_valid = re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", carrier_email) is not None

    docs, missing = _document_paths(claim.get("documents") or {})
    lines = []
    claimed = Decimal("0.00")
    items_confirmed = True
    for index, item in enumerate(claim.get("damaged_items") or [], 1):
        if not item.get("damaged"):
            continue
        description = str(item.get("description", "")).strip()
        try:
            quantity = int(item.get("quantity", 0))
        except (TypeError, ValueError):
            quantity = 0
        price = _money(item.get("invoice_unit_price"), f"damaged_items[{index}].invoice_unit_price")
        if not description or quantity < 1 or any(ord(char) < 32 for char in description):
            raise ValueError(f"damaged_items[{index}] needs a description and positive quantity")
        amount = (price * quantity).quantize(_MONEY)
        claimed += amount
        items_confirmed = items_confirmed and item.get("customer_confirmed") is True
        lines.append({"description": description, "quantity": quantity,
                      "invoice_unit_price": f"{price:.2f}", "claimed_value": f"{amount:.2f}",
                      "customer_confirmed": item.get("customer_confirmed") is True})

    terms = claim.get("carrier_terms") or {}
    terms_url = str(terms.get("source_url", "")).strip()
    parsed_terms = urlparse(terms_url)
    terms_valid = (parsed_terms.scheme == "https" and bool(parsed_terms.hostname)
                   and not parsed_terms.username and not parsed_terms.password
                   and not any(char.isspace() for char in terms_url))
    liability_estimate: Decimal | None = None
    if terms_valid and terms.get("liability_per_lb") is not None:
        try:
            per_lb = _money(terms.get("liability_per_lb"), "carrier_terms.liability_per_lb")
            weight = Decimal(str(shipment.get("weight_lb", "")))
            if per_lb > 0 and weight.is_finite() and weight > 0:
                liability_estimate = min(claimed, per_lb * weight).quantize(_MONEY)
        except (InvalidOperation, TypeError, ValueError):
            liability_estimate = None
    terms_valid = (terms_valid and liability_estimate is not None and bool(terms.get("effective_date"))
                   and terms.get("customer_confirmed") is True)

    separately_insured = bool(claim.get("separate_insurance"))
    explicit_insurance_request = bool(claim.get("customer_requests_claim"))
    insurance_blocked = separately_insured and not explicit_insurance_request
    if insurance_blocked:
        insurance_instruction = "confirm whether the customer wants a carrier claim despite separate insurance"
    elif separately_insured:
        insurance_instruction = "customer explicitly requested carrier claim despite separate insurance"
    else:
        insurance_instruction = "customer reports no separate shipment insurance"

    result = "match" if not missing and terms_valid and not insurance_blocked and lines and items_confirmed and email_valid else "uncertain — please check"
    draft = None
    if result == "match":
        tracking = tracking_number
        lines_text = "\n".join(f"- {row['quantity']} × {row['description']}: ${row['claimed_value']}"
                               for row in lines)
        draft = {
            "to": carrier_email,
            "subject": f"Freight claim — {tracking or shipment_id}",
            "body": (f"Please review this freight claim for shipment {shipment_id} ({tracking or 'tracking number not provided'}).\n\n"
                     f"Damaged invoice items only:\n{lines_text}\n\n"
                     f"Claimed invoice value: ${claimed:.2f}\n"
                     f"Estimated liability limit: ${liability_estimate:.2f} based on {terms_url} (effective {terms['effective_date']}).\n"
                     "The shipper has reviewed the attached documents and claim details. Please acknowledge receipt and provide a claim reference.\n"
                     "This draft has not been sent; the customer must review it and submit it through their chosen carrier channel."),
            "attachments": [path for paths in docs.values() for path in paths],
            "sent": False,
        }

    packet = {
        "venture": SLUG,
        "shipment_id": shipment_id,
        "carrier": shipment.get("carrier"),
        "tracking_number": shipment.get("tracking_number"),
        "result": result,
        "claimed_value": f"{claimed:.2f}",
        "damaged_items": lines,
        "liability_limit_estimate": f"{liability_estimate:.2f}" if liability_estimate is not None else None,
        "carrier_terms": {"source_url": terms_url or None, "effective_date": terms.get("effective_date"),
                          "customer_confirmed": terms.get("customer_confirmed") is True},
        "documents": docs,
        "missing_documents": missing,
        "damaged_item_values_confirmed_by_customer": items_confirmed,
        "insurance_instruction": insurance_instruction,
        "document_reads": _read_evidence(docs) if read_sources else [],
        "customer_email_draft": draft,
        "side_effects": [],
        "human_review_required": True,
    }
    if evidence_dir:
        destination = Path(evidence_dir)
        destination.mkdir(parents=True, exist_ok=True)
        packet_name = "claim-" + hashlib.sha256(shipment_id.encode("utf-8")).hexdigest()[:20] + ".json"
        path = destination / packet_name
        packet["packet_path"] = str(path)
        path.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return packet


def schedule_claim_deadlines(claim_id: str, carrier_received_date: str) -> None:
    """Schedule the carrier acknowledgment and resolution reminders once receipt is confirmed."""
    date.fromisoformat(carrier_received_date)
    add_deadline(claim_id, carrier_received_date, "30d|120d",
                 f"Freight claim {claim_id}: carrier acknowledgment and resolution")


def record_carrier_receipt(claim_id: str, carrier_received_date: str, reference: str,
                           confirmation_document: str, *, output_dir: str | Path | None = None) -> dict[str, Any]:
    """Record customer-provided submission confirmation and start the local 30/120-day clock."""
    received = date.fromisoformat(carrier_received_date)
    confirmation = Path(confirmation_document).expanduser().resolve()
    if not confirmation.is_file():
        raise ValueError("customer-provided carrier confirmation document is required")
    if not reference.strip():
        raise ValueError("carrier confirmation reference is required")
    schedule_claim_deadlines(claim_id, received.isoformat())
    record = {
        "claim_id": claim_id,
        "carrier_received_date": received.isoformat(),
        "carrier_reference": reference.strip(),
        "confirmation_document": str(confirmation),
        "deadline_rule": "30d|120d",
        "result": "match",
        "side_effects": [],
    }
    destination = Path(output_dir) if output_dir else Path(os.environ.get("GLACIER_HOME", "data")) / "ventures" / SLUG / "reports"
    destination.mkdir(parents=True, exist_ok=True)
    name = "receipt-" + hashlib.sha256(claim_id.encode("utf-8")).hexdigest()[:20] + ".json"
    path = destination / name
    record["record_path"] = str(path)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def build_contingency_invoice(claim_id: str, recovered_amount: Any, share_percent: Any) -> dict[str, Any]:
    """Calculate a review-only billing draft after recovery; never charge or send it."""
    recovered = _money(recovered_amount, "recovered_amount")
    share = Decimal(str(share_percent))
    if not share.is_finite() or not Decimal("20") <= share <= Decimal("30"):
        raise ValueError("share_percent must be between 20 and 30")
    amount = (recovered * share / Decimal("100")).quantize(_MONEY, rounding=ROUND_HALF_UP)
    return {
        "claim_id": claim_id,
        "recovered_amount": f"{recovered:.2f}",
        "share_percent": f"{share:.2f}",
        "invoice_amount": f"{amount:.2f}",
        "result": "match",
        "status": "pending approval",
        "sent": False,
        "charged": False,
    }


def record_first_ten_review(packet_id: str, approval_id: str, reviewer: str,
                           state_dir: str | Path) -> dict[str, Any]:
    """Record the owner gate for the first ten distinct packets in a local ledger."""
    if not re.fullmatch(r"[A-Za-z0-9_-]+", packet_id):
        raise ValueError("packet_id must contain only letters, numbers, hyphens, and underscores")
    if not reviewer.strip():
        raise ValueError("reviewer is required")
    database = Path(state_dir) / "first-ten-reviews.sqlite3"
    database.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database, timeout=30, isolation_level=None) as con:
        con.execute("CREATE TABLE IF NOT EXISTS packet_reviews (packet_id TEXT PRIMARY KEY, approval_id TEXT, reviewer TEXT NOT NULL, reviewed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        con.execute("BEGIN IMMEDIATE")
        prior = con.execute("SELECT approval_id, reviewer FROM packet_reviews WHERE packet_id=?", (packet_id,)).fetchone()
        if prior:
            con.execute("COMMIT")
            return {"packet_id": packet_id, "owner_approval_id": prior[0], "reviewer": prior[1],
                    "review_count": min(10, con.execute("SELECT COUNT(*) FROM packet_reviews WHERE approval_id IS NOT NULL").fetchone()[0]),
                    "first_ten_review_complete": con.execute("SELECT COUNT(*) FROM packet_reviews WHERE approval_id IS NOT NULL").fetchone()[0] >= 10}
        count = con.execute("SELECT COUNT(*) FROM packet_reviews WHERE approval_id IS NOT NULL").fetchone()[0]
        if count < 10 and not approval_id.strip():
            con.execute("ROLLBACK")
            raise ValueError("a Glacier owner approval ID is required for each of the first ten packets")
        con.execute("INSERT INTO packet_reviews(packet_id, approval_id, reviewer) VALUES(?,?,?)", (packet_id, approval_id.strip() or None, reviewer.strip()))
        con.execute("COMMIT")
        count = con.execute("SELECT COUNT(*) FROM packet_reviews WHERE approval_id IS NOT NULL").fetchone()[0]
    return {"packet_id": packet_id, "owner_approval_id": approval_id.strip() or None,
            "reviewer": reviewer.strip(), "review_count": min(10, count), "first_ten_review_complete": count >= 10}


def build_settlement_decision(offer: dict[str, Any], customer_decision: str | None) -> dict[str, Any]:
    """Record an explicit customer choice; accepting a full release closes the claim."""
    claim_id = str(offer.get("claim_id", "")).strip()
    if not claim_id:
        raise ValueError("settlement claim_id is required")
    amount = _money(offer.get("amount"), "settlement amount")
    full_release = offer.get("full_release") is True
    if not full_release:
        return {"claim_id": claim_id, "amount": f"{amount:.2f}", "result": "uncertain — please check",
                "status": "not a full-release offer", "claim_closed": False, "side_effects": []}
    if customer_decision not in {"accept", "decline"}:
        return {"claim_id": claim_id, "amount": f"{amount:.2f}", "full_release": True,
                "result": "uncertain — please check", "status": "awaiting customer decision",
                "claim_closed": False, "side_effects": []}
    accepted = customer_decision == "accept"
    return {"claim_id": claim_id, "amount": f"{amount:.2f}", "full_release": True,
            "customer_decision": customer_decision, "result": "match",
            "status": "accepted; claim closed" if accepted else "continue claim",
            "claim_closed": accepted, "side_effects": []}


def request_shipper_authorization(doc_path: str, signer: dict[str, Any]) -> dict[str, Any]:
    """Send an owner-provided authorization document to the shared local e-sign layer."""
    from ventures.blocks.customer import request_signature
    return request_signature(doc_path, signer)


def prepare_mock_carrier_form(portal_id: str, fields: dict[str, Any], auth: dict[str, Any]) -> dict[str, Any]:
    """Exercise the shared filer only against loopback mock portals."""
    host = urlparse(str(auth.get("base_url", ""))).hostname
    if host not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("freight claim form preparation is limited to a local mock portal")
    return prepare_portal_draft(portal_id, fields, auth)


def classify_shipments(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return possible exceptions for customer confirmation; never infer claim eligibility."""
    candidates = []
    for row in rows:
        searchable = " ".join(str(row.get(key, "")) for key in (
            "shipment_status", "tracking_status", "carrier_status", "exception_description", "status"))
        if re.search(r"damage|damaged|exception|lost|missing|shortage|undeliver", searchable, re.I):
            candidate = {
                "shipment_id": str(row.get("order_number") if str(row.get("shipment_id") or "").startswith("SS-ORD-")
                                    and row.get("order_number") else row.get("shipment_id") or row.get("id") or ""),
                "signal": "possible damage or delivery exception",
                "customer_confirmation_required": True,
            }
            if row.get("tracking_number"):
                candidate["tracking_number"] = row["tracking_number"]
            candidates.append(candidate)
    return candidates


def _newest_shipstation_csv(incoming: Path) -> Path | None:
    files = [path for path in incoming.glob("*.csv") if path.is_file()]
    return sorted(files, key=lambda path: (-path.stat().st_mtime_ns, path.name.casefold()))[0] if files else None


def _shipment_report(rows: list[dict[str, Any]], *, source: str, today: str,
                     api_error: str | None = None, csv_file: Path | None = None,
                     skipped_rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    candidates = classify_shipments(rows)
    record: dict[str, Any] = {
        "result": "match" if candidates else f"no match found in ShipStation as of {today}",
        "checked_on": today,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "source": source,
        "side_effects": [],
    }
    if api_error:
        record["api_error"] = api_error
    if csv_file:
        record["csv_file"] = str(csv_file)
    if skipped_rows is not None:
        record["skipped_rows"] = skipped_rows
    return record


def _read_api_shipments(shipment_client: Any) -> tuple[list[dict[str, Any]], list[dict[str, str]], int]:
    rows = shipment_client.get_shipments(page_size=100, max_pages=20)
    enriched = []
    untracked = []
    lookups = 0
    for shipment in rows:
        labels = shipment.get("labels") if isinstance(shipment.get("labels"), list) else []
        label_id = shipment.get("label_id") or next((label.get("label_id") or label.get("labelId")
                                                       for label in labels if isinstance(label, dict)), None)
        if not label_id:
            untracked.append({"shipment_id": str(shipment.get("shipment_id") or shipment.get("id") or ""),
                              "reason": "ShipStation record has no label id for a tracking read"})
            continue
        if lookups >= MAX_TRACKING_LOOKUPS:
            untracked.append({"shipment_id": str(shipment.get("shipment_id") or shipment.get("id") or ""),
                              "reason": "daily tracking lookup limit reached"})
            continue
        tracking = shipment_client.get_tracking_for_label(str(label_id))
        lookups += 1
        enriched.append({**shipment, **tracking})
    return enriched, untracked, lookups


def watch_shipments(*, client: Any = None, enabled: bool | None = None,
                    csv_path: str | Path | None = None) -> dict[str, Any]:
    """Use a working opted-in API, falling back to an explicit or newest local CSV."""
    home = Path(os.environ.get("GLACIER_HOME", "data")) / "ventures" / SLUG
    incoming = home / "incoming"
    opt_in = home / "shipstation-enabled.json"
    approved = enabled if enabled is not None else (
        opt_in.is_file() and json.loads(opt_in.read_text(encoding="utf-8")).get("approved") is True
    )
    today = date.today().isoformat()
    selected_csv = Path(csv_path).expanduser() if csv_path is not None else _newest_shipstation_csv(incoming)
    api_error = None
    if csv_path is not None:
        approved = False
    elif approved:
        shipment_client = client or FreightShipStationReader()
        try:
            rows, untracked, lookups = _read_api_shipments(shipment_client)
            record = _shipment_report(rows, source="api", today=today)
            record["untracked_shipments"] = untracked
            record["tracking_lookups"] = lookups
            if not record["candidates"] and untracked:
                record["result"] = "uncertain — please check"
        except ConnectorError as exc:
            api_error = str(exc)
        finally:
            if client is None:
                shipment_client.close()
        if api_error is None:
            output = home / "reports"
            output.mkdir(parents=True, exist_ok=True)
            (output / "shipstation-candidates.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
            return record

    if selected_csv is not None:
        try:
            rows, skipped = parse_shipments_csv(selected_csv)
            record = _shipment_report(rows, source="csv", today=today, api_error=api_error,
                                      csv_file=selected_csv, skipped_rows=skipped)
        except (OSError, ValueError) as exc:
            record = {"result": "uncertain — please check", "checked_on": today,
                      "reason": f"Could not read ShipStation CSV: {exc}", "source": "csv",
                      "csv_file": str(selected_csv), "api_error": api_error,
                      "candidate_count": 0, "candidates": [], "skipped_rows": [], "side_effects": []}
    elif not approved:
        record = {"result": "uncertain — please check", "checked_on": today,
                  "reason": "ShipStation reads are disabled until the owner enables them after checking API plan limits; no ShipStation CSV was found in incoming/.",
                  "candidate_count": 0, "candidates": [], "source": "unavailable", "side_effects": []}
    else:
        record = {"result": "uncertain — please check", "checked_on": today,
                  "reason": api_error or "ShipStation could not be read and no CSV export was found in incoming/.",
                  "api_error": api_error, "candidate_count": 0, "candidates": [],
                  "source": "unavailable", "side_effects": []}
    output = home / "reports"
    output.mkdir(parents=True, exist_ok=True)
    (output / "shipstation-candidates.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def remind(on_date: date | None = None) -> dict[str, Any]:
    """Collect one-time local claim deadline reminders for today's date."""
    target = on_date or date.today()
    reminders = due_deadlines(target)
    record = {"result": "match" if reminders else f"no match found in freight claim deadlines as of {target.isoformat()}",
              "checked_on": target.isoformat(), "reminders": reminders, "side_effects": []}
    output = Path(os.environ.get("GLACIER_HOME", "data")) / "ventures" / SLUG / "reports"
    output.mkdir(parents=True, exist_ok=True)
    (output / "deadlines.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return record


def prepare_file(input_path: str, output_dir: str | None) -> dict[str, Any]:
    data = json.loads(Path(input_path).read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else [data]
    destination = Path(output_dir) if output_dir else Path(os.environ.get("GLACIER_HOME", "data")) / "ventures" / SLUG / "packets"
    results = [build_claim_packet(item, evidence_dir=destination) for item in items]
    return {"result": "match" if all(item["result"] == "match" for item in results) else "uncertain — please check",
            "packets": results, "side_effects": []}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    watch = commands.add_parser("watch", help="read ShipStation or the newest shipment CSV and save exception candidates")
    watch.add_argument("--csv", help="use this ShipStation CSV instead of the API")
    commands.add_parser("remind", help="collect today's carrier deadline reminders")
    prepare = commands.add_parser("prepare", help="prepare claim packet drafts from customer-confirmed intake JSON")
    prepare.add_argument("--input", required=True)
    prepare.add_argument("--output-dir")
    invoice = commands.add_parser("invoice", help="prepare a contingency invoice draft after confirmed recovery")
    invoice.add_argument("--input", required=True)
    invoice.add_argument("--output")
    signature = commands.add_parser("signature", help="create a local signature request from an owner-approved authorization document")
    signature.add_argument("--document", required=True)
    signature.add_argument("--signer", required=True)
    signature.add_argument("--output")
    receipt = commands.add_parser("receipt", help="record customer-provided carrier receipt confirmation")
    receipt.add_argument("--input", required=True)
    receipt.add_argument("--output-dir")
    deadline = commands.add_parser("deadline", help="record the carrier-confirmed receipt date")
    deadline.add_argument("--claim-id", required=True)
    deadline.add_argument("--received-date", required=True)
    owner_review = commands.add_parser("owner-review", help="record the Glacier approval for a packet")
    owner_review.add_argument("--packet-id")
    owner_review.add_argument("--input")
    owner_review.add_argument("--approval", default="")
    owner_review.add_argument("--reviewer", required=True)
    owner_review.add_argument("--state-dir")
    settlement = commands.add_parser("settlement", help="record the customer's accept or decline choice for a full-release offer")
    settlement.add_argument("--input", required=True)
    settlement.add_argument("--approval", required=True)
    settlement.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        if args.command == "watch":
            result = watch_shipments(csv_path=args.csv)
        elif args.command == "remind":
            result = remind()
        elif args.command == "prepare":
            result = prepare_file(args.input, args.output_dir)
        elif args.command == "invoice":
            recovery = json.loads(Path(args.input).read_text(encoding="utf-8"))
            result = build_contingency_invoice(recovery["claim_id"], recovery["recovered_amount"], recovery["share_percent"])
            output = Path(args.output) if args.output else Path(os.environ.get("GLACIER_HOME", "data")) / "ventures" / SLUG / "reports" / "invoice-draft.json"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        elif args.command == "signature":
            signer = json.loads(Path(args.signer).read_text(encoding="utf-8"))
            result = request_shipper_authorization(args.document, signer)
            output = Path(args.output) if args.output else Path(os.environ.get("GLACIER_HOME", "data")) / "ventures" / SLUG / "reports" / "signature-request.json"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        elif args.command == "receipt":
            submitted = json.loads(Path(args.input).read_text(encoding="utf-8"))
            result = record_carrier_receipt(submitted["claim_id"], submitted["carrier_received_date"],
                                            submitted["reference"], submitted["confirmation_document"],
                                            output_dir=args.output_dir)
        elif args.command == "owner-review":
            state_dir = args.state_dir or Path(os.environ.get("GLACIER_HOME", "data")) / "ventures" / SLUG / "reviews"
            if args.input:
                source = json.loads(Path(args.input).read_text(encoding="utf-8"))
                claims = source if isinstance(source, list) else [source]
                if len(claims) != 1:
                    raise ValueError("Run one claim packet per owner approval so the first-ten review is distinct and auditable")
                result = [record_first_ten_review(str(item["shipment"]["shipment_id"]), args.approval, args.reviewer, state_dir) for item in claims]
            elif args.packet_id:
                result = record_first_ten_review(args.packet_id, args.approval, args.reviewer, state_dir)
            else:
                raise ValueError("owner-review requires --packet-id or --input")
        elif args.command == "settlement":
            offer = json.loads(Path(args.input).read_text(encoding="utf-8"))
            result = build_settlement_decision(offer, offer.get("customer_decision"))
            result["glacier_approval_id"] = args.approval
            output = Path(args.output) if args.output else Path(os.environ.get("GLACIER_HOME", "data")) / "ventures" / SLUG / "reports" / "settlement-decision.json"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        else:
            schedule_claim_deadlines(args.claim_id, args.received_date)
            result = {"claim_id": args.claim_id, "carrier_received_date": args.received_date,
                      "rule": "30d|120d", "result": "match"}
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 1 if args.command == "settlement" and result.get("result") != "match" else 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({"result": "uncertain — please check", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
