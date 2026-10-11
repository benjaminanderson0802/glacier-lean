"""Prepare customer-reviewed cosmetic product listing packets; never sign or submit."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from ventures.blocks.deadlines import add as add_deadline, due as due_deadlines
from ventures.blocks.reader import read_document
from ventures.blocks.rules import check as check_rules

FDA_FORM = "https://www.fda.gov/cosmetics/registration-listing-cosmetic-product-facilities-and-products/form-fda-5067-cosmetic-product-listing"
FDA_SPL_GUIDE = "https://www.fda.gov/media/84201/download"
NS = "urn:hl7-org:v3"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
ET.register_namespace("", NS)
ET.register_namespace("xsi", XSI)


def _s(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _field(value: Any, *, source: str, uncertain: bool = False, confidence: float | None = None,
           page: int | None = None) -> dict[str, Any]:
    needs_confirmation = uncertain or value in (None, "", [])
    return {"value": value, "source": source, "page": page,
            "confidence": confidence if confidence is not None else (0.0 if value in (None, "", []) else (0.5 if needs_confirmation else 1.0)),
            "uncertain": needs_confirmation}


def _first(items: list[dict[str, Any]], path: str) -> ET.Element:
    return ET.SubElement(items[-1], f"{{{NS}}}{path}")


def _build_spl(payload: dict[str, Any], root_id: str, submitted_on: date) -> bytes:
    root = ET.Element(f"{{{NS}}}document", {f"{{{XSI}}}schemaLocation": f"{NS} https://www.accessdata.fda.gov/spl/schema/spl.xsd"})
    ET.SubElement(root, f"{{{NS}}}id", {"root": root_id})
    ET.SubElement(root, f"{{{NS}}}code", {"code": "103572-4", "codeSystem": "2.16.840.1.113883.6.1", "displayName": "Cosmetic Product Listing"})
    ET.SubElement(root, f"{{{NS}}}effectiveTime", {"value": submitted_on.strftime("%Y%m%d")})
    ET.SubElement(root, f"{{{NS}}}setId", {"root": str(payload.get("set_id") or root_id)})
    ET.SubElement(root, f"{{{NS}}}versionNumber", {"value": "1"})

    author = ET.SubElement(root, f"{{{NS}}}author")
    ET.SubElement(author, f"{{{NS}}}time", {"value": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S+0000")})
    assigned = ET.SubElement(author, f"{{{NS}}}assignedEntity")
    represented = ET.SubElement(assigned, f"{{{NS}}}representedOrganization")
    ET.SubElement(represented, f"{{{NS}}}name").text = _s(payload["responsible_person_name"])
    ET.SubElement(represented, f"{{{NS}}}telecom", {"value": f"tel:{_s(payload['responsible_person_phone'])}"})

    registrant_entity = ET.SubElement(represented, f"{{{NS}}}assignedEntity")
    registrant = ET.SubElement(registrant_entity, f"{{{NS}}}assignedOrganization")
    for facility in payload.get("facilities", []):
        facility_entity = ET.SubElement(registrant, f"{{{NS}}}assignedEntity")
        organization = ET.SubElement(facility_entity, f"{{{NS}}}assignedOrganization")
        fei = _s(facility.get("fei"))
        if fei:
            ET.SubElement(organization, f"{{{NS}}}id", {"extension": fei, "root": "2.16.840.1.113883.4.82"})
        else:
            ET.SubElement(organization, f"{{{NS}}}name").text = _s(facility.get("name"))
            addr = ET.SubElement(organization, f"{{{NS}}}addr")
            for key, tag in (("street", "streetAddressLine"), ("city", "city"), ("state", "state"), ("postal_code", "postalCode")):
                if _s(facility.get(key)):
                    ET.SubElement(addr, f"{{{NS}}}{tag}").text = _s(facility[key])
            if _s(facility.get("country")):
                country = _s(facility["country"])
                ET.SubElement(addr, f"{{{NS}}}country", {"code": country, "codeSystem": "1.0.3166.1.2.3"}).text = country
            if facility.get("exempt_confirmed"):
                subject = ET.SubElement(facility_entity, f"{{{NS}}}subjectOf")
                characteristic = ET.SubElement(subject, f"{{{NS}}}characteristic", {"classCode": "OBS"})
                ET.SubElement(characteristic, f"{{{NS}}}code", {"code": "SPLSMALLBUSINESS", "codeSystem": "2.16.840.1.113883.1.11.19255"})
                ET.SubElement(characteristic, f"{{{NS}}}value", {f"{{{XSI}}}type": "BL", "value": "true"})
        role = _s(payload["responsible_person_role"])
        role_codes = {"manufacturer": ("C43360", "manufacture"), "packer": ("C84731", "pack"), "distributor": ("C201565", "distribute")}
        code, display = role_codes[role]
        performance = ET.SubElement(facility_entity, f"{{{NS}}}performance")
        act = ET.SubElement(performance, f"{{{NS}}}actDefinition")
        ET.SubElement(act, f"{{{NS}}}code", {"code": code, "codeSystem": "2.16.840.1.113883.3.26.1.1", "displayName": display})
        product_ref = ET.SubElement(act, f"{{{NS}}}product")
        product = ET.SubElement(product_ref, f"{{{NS}}}manufacturedProduct", {"classCode": "MANU"})
        material = ET.SubElement(product, f"{{{NS}}}manufacturedMaterialKind")
        ET.SubElement(material, f"{{{NS}}}code")
        ET.SubElement(material, f"{{{NS}}}name").text = _s(payload["product_name"])

    component = ET.SubElement(root, f"{{{NS}}}component")
    structured_body = ET.SubElement(component, f"{{{NS}}}structuredBody")
    section_component = ET.SubElement(structured_body, f"{{{NS}}}component")
    section = ET.SubElement(section_component, f"{{{NS}}}section")
    ET.SubElement(section, f"{{{NS}}}id", {"root": str(uuid.uuid4())})
    for facility in payload.get("facilities", []):
        product_subject = ET.SubElement(section, f"{{{NS}}}subject")
        outer = ET.SubElement(product_subject, f"{{{NS}}}manufacturedProduct")
        inner = ET.SubElement(outer, f"{{{NS}}}manufacturedProduct")
        ET.SubElement(inner, f"{{{NS}}}code")
        ET.SubElement(inner, f"{{{NS}}}name").text = _s(payload["product_name"])
        for code in payload["product_category_codes"]:
            kind = ET.SubElement(inner, f"{{{NS}}}asSpecializedKind")
            material_kind = ET.SubElement(kind, f"{{{NS}}}generalizedMaterialKind")
            ET.SubElement(material_kind, f"{{{NS}}}code", {"code": _s(code), "codeSystem": "2.16.840.1.113883.6.345"})
        for ingredient in payload["ingredients"]:
            row = ET.SubElement(inner, f"{{{NS}}}ingredient", {"classCode": "INGR"})
            substance = ET.SubElement(row, f"{{{NS}}}ingredientSubstance")
            ET.SubElement(substance, f"{{{NS}}}name").text = _s(ingredient)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _reader_review(payload: dict[str, Any]) -> tuple[list[str], dict[str, Any] | None]:
    path = payload.get("ingredient_document")
    if not path:
        return ["ingredient label/source document"], None
    source_path = Path(os.path.expandvars(str(path))).expanduser()
    try:
        parsed = read_document(source_path, schema={"ingredients": ["Ingredients", "Ingredient list"]})
    except Exception as exc:
        # Document libraries raise format-specific exceptions (for example,
        # pdfplumber's PdfminerException) for corrupt uploads. Preserve the
        # customer review path instead of letting an unreadable label crash a run.
        return ["ingredient label/source document"], {"error": f"{type(exc).__name__}: {exc}"}
    value = parsed.get("fields", {}).get("ingredients", {})
    if value.get("uncertain") or not value.get("value"):
        return ["ingredients"], parsed
    source_ingredients = [part.strip() for part in re.split(r"[,;\n]+", str(value["value"])) if part.strip()]
    supplied = [_s(part) for part in payload.get("ingredients", [])]
    if [part.casefold() for part in source_ingredients] != [part.casefold() for part in supplied]:
        return ["ingredients"], parsed
    return [], parsed


def _rules_fields(payload: dict[str, Any], *, unresolved: list[str]) -> dict[str, Any]:
    ingredients = payload.get("ingredients")
    facility_fei = payload.get("facility_fei") or []
    if not facility_fei and payload.get("facility_exempt") is True and payload.get("facility_exemption_confirmed") is True:
        facility_fei = ["brand-confirmed exempt facility"]
    product_name = payload.get("product_name")
    values = {
        "responsible_person_name": payload.get("responsible_person_name"),
        "responsible_person_phone": payload.get("responsible_person_phone"),
        "product_category_codes": payload.get("product_category_codes"),
        "product_name": product_name,
        "fragrance_or_flavor": payload.get("fragrance_or_flavor"),
        "facility_fei": facility_fei,
        "ingredients": ingredients,
        "ingredient_products": {item: [product_name] for item in ingredients or []} if product_name else {},
    }
    source_root = _s(payload.get("_source_root")) or "brand-details.json"
    source_map = payload.get("_field_sources") or {}
    fields = {
        name: _field(value, source=source_map.get(name, f"{source_root}#/{name}"), uncertain=name in unresolved)
        for name, value in values.items()
    }
    facilities = payload.get("facilities") or []
    supplement = {
        "responsible_person_role": payload.get("responsible_person_role"),
        "facilities": facilities,
        "first_market_date": payload.get("first_market_date"),
        "last_listing_date": payload.get("last_listing_date"),
        "exemption_checklist": payload.get("exemption_checklist"),
        "customer_confirmed": payload.get("customer_confirmed"),
        "shopify_title": payload.get("shopify_title"),
    }
    for name, value in supplement.items():
        field_source = source_map.get(name, f"{source_root}#/{name}")
        # Shopify's title is useful cross-reference data, but is not the label identity required by Form 5067.
        field_uncertain = name == "shopify_title" or name in unresolved
        if name == "customer_confirmed" and value is not True:
            field_uncertain = True
        if name in {"responsible_person_role", "first_market_date", "last_listing_date", "exemption_checklist"} and value in (None, "", {}):
            field_uncertain = True
        if name == "facilities" and not value:
            field_uncertain = True
        fields[name] = _field(value, source=field_source, uncertain=field_uncertain)
    return fields


def _validate_payload(payload: dict[str, Any], as_of: date, reader_uncertain: list[str]) -> dict[str, Any]:
    product_name = _s(payload.get("product_name"))
    ingredients = payload.get("ingredients")
    unresolved = list(reader_uncertain)
    checklist = payload.get("exemption_checklist") or {}
    checklist_fields = ("small_business", "product_may_be_covered_exception", "customer_wants_listing")
    if any(not isinstance(checklist.get(key), bool) for key in checklist_fields):
        unresolved.append("brand-confirmed exemption checklist")
    if payload.get("customer_confirmed") is not True:
        unresolved.append("customer checklist")
        unresolved.extend(("responsible_person_name", "responsible_person_phone", "product_category_codes",
                          "product_name", "fragrance_or_flavor", "facility_fei", "ingredients",
                          "responsible_person_role", "facilities", "first_market_date", "last_listing_date",
                          "exemption_checklist"))
    if not product_name or not ingredients or not payload.get("facilities"):
        unresolved.append("product, ingredients, or facilities")
    if any(not _s(value) for value in ingredients or []):
        unresolved.append("ingredients")
    if any(not (facility.get("fei") or (facility.get("name") and facility.get("exempt_confirmed") is True)) for facility in payload.get("facilities", [])):
        unresolved.append("facility identifier or customer-confirmed small business exemption")
    role = payload.get("responsible_person_role")
    if role not in {"manufacturer", "packer", "distributor"}:
        unresolved.append("responsible person business type")
    if any(not re.fullmatch(r"\d{7}|\d{10}", _s(facility.get("fei"))) for facility in payload.get("facilities", []) if facility.get("fei")):
        unresolved.append("facility FEI")
    if len({name.casefold() for name in [product_name]}) != 1:
        unresolved.append("unique product name")
    fields = _rules_fields(payload, unresolved=unresolved)
    rules = check_rules(fields, "fda_mocra_listing.json")
    # Rules use the shared checker; this final status layer adds customer confirmation
    # and the SPL-specific facility requirements from FDA's published guidance.
    if unresolved:
        rules["verdict"] = "uncertain" if not any(r["verdict"] == "fail" for r in rules["results"]) else "fail"
    return {"rules": rules, "fields": fields, "please_confirm": sorted(set(unresolved)), "product_name": product_name}


def _ingredient_checklist(payload: dict[str, Any], reader_data: dict[str, Any] | None) -> list[dict[str, Any]]:
    ingredient_field = (reader_data or {}).get("fields", {}).get("ingredients", {})
    label_path = payload.get("ingredient_document")
    reader_value = ingredient_field.get("value")
    supplied = [_s(part) for part in payload.get("ingredients", [])]
    extracted = [part.strip() for part in re.split(r"[,;\n]+", str(reader_value or "")) if part.strip()]
    order_matches = bool(extracted) and [part.casefold() for part in extracted] == [part.casefold() for part in supplied]
    brand_confirmed = payload.get("customer_confirmed") is True
    label_source = str(label_path) if label_path else None
    return [
        {"field": "ingredient_order", "checked": order_matches, "uncertain": not (order_matches and brand_confirmed),
         "source": label_source or "missing: brand label/source document", "detail": "Compare the ingredient sequence with the package label."},
        {"field": "label_source", "checked": bool(label_source and ingredient_field and not ingredient_field.get("uncertain") and brand_confirmed),
         "uncertain": not bool(label_source and ingredient_field and not ingredient_field.get("uncertain") and brand_confirmed),
         "source": label_source or "missing: brand label/source document", "detail": "Confirm this is the current product label and the extracted text is readable."},
        {"field": "brand_confirmation", "checked": brand_confirmed,
         "uncertain": not brand_confirmed, "source": "brand-details.json#/customer_confirmed",
         "detail": "The responsible person confirms every ingredient and its label order."},
    ]


def _reminder_dates(payload: dict[str, Any]) -> dict[str, str | None]:
    first_market = _s(payload.get("first_market_date"))
    last_listing = _s(payload.get("last_listing_date"))
    try:
        initial_due = (date.fromisoformat(first_market) + timedelta(days=120)).isoformat() if first_market else None
    except ValueError:
        initial_due = None
    try:
        annual_review = (date.fromisoformat(last_listing) + timedelta(days=365)).isoformat() if last_listing else None
    except ValueError:
        annual_review = None
    return {"first_marketed": first_market or None, "initial_listing_due": initial_due, "annual_update_review": annual_review}


def _write_packet(payload: dict[str, Any], output_dir: Path, as_of: date) -> tuple[str, str]:
    root_id = str(uuid.uuid4())
    xml_name = f"{root_id}.xml"
    zip_name = f"fda-cosmetics-{root_id}.zip"
    xml_data = _build_spl(payload, root_id, as_of)
    output_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_dir / zip_name, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(xml_name, xml_data)
    return zip_name, xml_name


def prepare_listing(payload: dict[str, Any], output_dir: str | Path, *, as_of: str | date | None = None) -> dict[str, Any]:
    today = date.fromisoformat(as_of) if isinstance(as_of, str) else as_of or date.today()
    reader_uncertain, reader_data = _reader_review(payload)
    review = _validate_payload(payload, today, reader_uncertain)
    source_map = payload.get("_field_sources") or {}
    if "ingredients" in review["fields"]:
        reader_ingredient = (reader_data or {}).get("fields", {}).get("ingredients", {})
        label_path = payload.get("ingredient_document")
        review["fields"]["ingredients"]["source"] = source_map.get(
            "ingredients", f"label:{label_path or 'missing source document'}"
        )
        review["fields"]["ingredients"]["page"] = reader_ingredient.get("page")
        if reader_ingredient.get("confidence") is not None:
            review["fields"]["ingredients"]["confidence"] = reader_ingredient["confidence"]
        if reader_ingredient.get("uncertain"):
            review["fields"]["ingredients"]["uncertain"] = True
    for checklist_item in payload.get("exemption_checklist", {}) or {}:
        review["fields"][f"exemption_{checklist_item}"] = _field(
            payload["exemption_checklist"][checklist_item],
            source=f"{payload.get('_source_root', 'brand-details.json')}#/exemption_checklist/{checklist_item}",
            uncertain=not isinstance(payload["exemption_checklist"][checklist_item], bool) or payload.get("customer_confirmed") is not True,
        )
    if review["please_confirm"] or review["rules"]["verdict"] != "pass":
        result = "uncertain — please check"
    elif not payload.get("exemption_checklist", {}).get("customer_wants_listing"):
        result = "uncertain — please check"
        review["please_confirm"].append("brand must confirm whether this product should be included in the listing packet")
    else:
        result = "match"
    zip_name = xml_name = None
    if result == "match":
        zip_name, xml_name = _write_packet(payload, Path(output_dir), today)
        product_id = str(payload.get("shopify_id") or payload.get("product_name") or "product")
        if payload.get("first_market_date"):
            add_deadline(f"fda-120-{product_id}", _s(payload["first_market_date"]), "120d", f"FDA listing review: {review['product_name']} (120 days after first marketing)")
        if payload.get("last_listing_date"):
            add_deadline(f"fda-annual-{product_id}", _s(payload["last_listing_date"]), "365d", f"FDA annual listing update review: {review['product_name']}")
    report = {
        "result": result,
        "customer_must_submit": True,
        "submitted": False,
        "signed": False,
        "spl_zip": zip_name,
        "spl_xml": xml_name,
        "rules": review["rules"],
        "fields": review["fields"],
        "ingredient_checklist": _ingredient_checklist(payload, reader_data),
        "reminders": _reminder_dates(payload),
        "please_confirm": review["please_confirm"],
        "reader": reader_data,
        "sources": {"fda_form": FDA_FORM, "fda_spl_validation_guide": FDA_SPL_GUIDE},
        "generated_at": today.isoformat(),
        "instruction": "The brand reviews, signs where required, uploads the ZIP to FDA Cosmetics Direct, and submits. Glacier never signs or submits.",
    }
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    (Path(output_dir) / "listing-packet.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def parse_response(path: str | Path) -> dict[str, Any]:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    confirmation = re.search(r"(?:confirmation\s*(?:number|id)?\s*[:#]\s*)([A-Za-z0-9-]+)", text, re.IGNORECASE)
    if re.search(r"submission\s+accepted", text, re.IGNORECASE):
        status = "match"
    elif re.search(r"rejected|validation\s+error", text, re.IGNORECASE):
        status = "uncertain — please check"
    else:
        status = "uncertain — please check"
    return {"status": status, "confirmation": confirmation.group(1) if confirmation else None, "submitted_by_glacier": False}


def _prepare_from_shopify(shop: str, details_path: Path, output: Path, as_of: str | None) -> dict[str, Any]:
    from ventures.blocks.connectors import ConnectorError, ShopifyClient

    if not details_path.is_file():
        output.mkdir(parents=True, exist_ok=True)
        summary = {"shop": shop, "products_read": 0, "products": [], "submitted": False, "ready": False,
                   "setup_required": f"Save brand-confirmed product details at {details_path}; include ingredients, label sources, facility details, and listing dates. No product data was read and no packet was made."}
        (output / "shopify-listing-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary
    details = json.loads(details_path.read_text(encoding="utf-8"))
    try:
        client = ShopifyClient(shop)
        try:
            products = client.get_products()
        finally:
            client.close()
    except (ConnectorError, ValueError):
        output.mkdir(parents=True, exist_ok=True)
        summary = {"shop": shop, "products_read": 0, "products": [], "submitted": False, "ready": False,
                   "setup_required": "Complete the Shopify connection step in your steps, then run again. No product data was read and no packet was made."}
        (output / "shopify-listing-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary
    details_by_id = details.get("products", {})
    results = []
    for product in products:
        extra = details_by_id.get(product.get("id"))
        if not extra:
            results.append({"shopify_id": product.get("id"), "shopify_title": product.get("title"), "result": "uncertain — please check", "please_confirm": ["product ingredients, label name, category codes, facilities, and customer checklist"]})
            continue
        source_root = details_path.name
        source_map = {key: f"{source_root}#/brand/{key}" for key in details.get("brand", {})}
        source_map.update({key: f"{source_root}#/products/{product.get('id')}/{key}" for key in extra})
        source_map["shopify_title"] = f"Shopify GraphQL products.edges[].node.title ({product.get('id')})"
        source_map["ingredients"] = f"label:{extra.get('ingredient_document') or 'missing source document'}"
        payload = {**details.get("brand", {}), **extra, "shopify_id": product.get("id"), "shopify_title": product.get("title"),
                   "_source_root": source_root, "_field_sources": source_map}
        results.append(prepare_listing(payload, output / re.sub(r"[^a-zA-Z0-9-]+", "-", product.get("handle") or product.get("id", "product")), as_of=as_of))
    summary = {"shop": shop, "products_read": len(products), "products": results, "submitted": False, "ready": bool(results) and all(item.get("result") == "match" for item in results)}
    output.mkdir(parents=True, exist_ok=True)
    (output / "shopify-listing-summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    prepare = sub.add_parser("prepare", help="read Shopify and prepare local customer-reviewed packets")
    prepare.add_argument("--shop", required=True, help="Shopify *.myshopify.com domain")
    prepare.add_argument("--details", type=Path, required=True, help="brand-confirmed product and facility JSON keyed by Shopify product ID")
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("--as-of")
    due = sub.add_parser("due", help="print any local FDA listing deadline reminders due today")
    due.add_argument("--on")
    response = sub.add_parser("response", help="parse an FDA response file forwarded by the customer")
    response.add_argument("--file", type=Path, required=True)
    response.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.action == "prepare":
        result = _prepare_from_shopify(args.shop, args.details, args.output, args.as_of)
    elif args.action == "due":
        result = due_deadlines(args.on or date.today())
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result else 3
    else:
        result = parse_response(args.file)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    # Missing Shopify access is an expected owner setup step. Keep the
    # flow healthy so Glacier can present its explicit setup/review prompt.
    return 0 if result.get("ready", True) or result.get("setup_required") else 1


if __name__ == "__main__":
    raise SystemExit(main())
