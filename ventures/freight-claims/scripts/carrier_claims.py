"""Carrier-specific claim packet guidance and customer-confirmed date tracking."""
from __future__ import annotations

import calendar
from datetime import date, timedelta
from typing import Any


_COMMON_EVIDENCE = [
    "tracking number or carrier PRO/reference",
    "bill of lading or shipping receipt",
    "itemized commercial invoice or other proof of value",
    "delivery receipt / proof of delivery, including any exception notation",
    "claim amount tied to customer-confirmed damaged, lost, or short items",
]

_GUIDANCE: dict[str, dict[str, Any]] = {
    "ups": {
        "carrier": "UPS",
        "filing_deadline_days": 60,
        "filing_deadline_months": None,
        "filing_deadline_anchor": "scheduled_delivery_date",
        "deadline_note": "Start a lost or damaged package claim within 60 days of scheduled delivery; confirm the exact service and shipment terms.",
        "deadline_requires_service_lookup": False,
        "required_evidence": _COMMON_EVIDENCE + [
            "invoice or other merchandise-value support",
            "three damage photos: item as packed, close-up shipping label, and outside package damage",
            "package dimensions for damage claims; retain contents and packaging for possible inspection",
        ],
        "sources": [
            {"title": "UPS File a Claim", "url": "https://www.ups.com/us/en/support/file-a-claim"},
            {"title": "UPS Supporting Documents for Claims", "url": "https://www.ups.com/us/en/support/file-a-claim/supporting-documents"},
        ],
    },
    "fedex": {
        "carrier": "FedEx",
        "filing_deadline_days": 60,
        "filing_deadline_months": None,
        "filing_deadline_anchor": "shipment_date",
        "deadline_note": "Damage/missing contents: 60 calendar days from shipment date for U.S. packages, 21 days for international. Lost shipment: 9 months from shipment date.",
        "deadline_requires_service_lookup": False,
        "required_evidence": _COMMON_EVIDENCE + [
            "FedEx airbill / Ship Manager printout or pickup record, when available",
            "photos of the package and damaged contents; keep original packaging until resolved",
            "original vendor invoice, retail receipt, or online order proof of payment",
            "itemized repair invoice or statement of non-repair, appraisal, or expense statement when applicable",
            "serial numbers for damaged or lost merchandise when available",
        ],
        "sources": [
            {"title": "FedEx Claims", "url": "https://www.fedex.com/en-us/customer-support/claims.html"},
        ],
    },
    "usps": {
        "carrier": "USPS",
        "filing_deadline_days": 60,
        "filing_deadline_months": None,
        "filing_deadline_anchor": "mailing_date",
        "deadline_note": "Damage/missing contents: file immediately, no later than 60 days after mailing. Lost-mail windows depend on mail class and service; check the current DMM 609 chart before calculating.",
        "deadline_requires_service_lookup": True,
        "required_evidence": _COMMON_EVIDENCE + [
            "proof of insurance / purchased service (mailing receipt, label record, or other accepted record)",
            "proof of value (paid invoice, sales receipt, or acceptable transaction record)",
            "damage photos and repair estimate when applicable",
            "retain damaged item, mailing container, packaging, and contents for possible Post Office inspection",
        ],
        "sources": [
            {"title": "USPS Domestic Claims - The Basics", "url": "https://faq.usps.com/articles/Knowledge/Domestic-Claims-The-Basics"},
            {"title": "USPS Domestic Mail Manual 609", "url": "https://pe.usps.com/TEXT/DMM300/609.htm"},
        ],
    },
    "ltl": {
        "carrier": "LTL (NMFC / Carmack review)",
        "filing_deadline_days": None,
        "filing_deadline_months": 9,
        "filing_deadline_anchor": "delivery_date_or_reasonable_time_for_delivery_if_not_delivered",
        "deadline_note": "If Carmack applies, federal law sets a minimum 9-month filing period; the bill of lading/tariff and claim context control the actual deadline. Do not treat this estimate as legal advice.",
        "deadline_requires_service_lookup": True,
        "required_evidence": [
            "written claim with shipment identity, asserted liability, and a determinable amount",
            "signed bill of lading and delivery receipt / proof of delivery with exceptions noted",
            "freight bill and proof of freight charges",
            "itemized invoice / proof of value, with claimed quantity, unit value, and arithmetic",
            "NMFC item number and freight class, commodity description, packaging, and shipment weight as tendered",
            "dated photos of commodity, packaging, pallet, and shipping labels; inspection report and salvage/repair estimate when available",
            "carrier correspondence, claim receipt/reference, and customer-confirmed dates",
        ],
        "sources": [
            {"title": "49 U.S.C. § 14706 (Carmack Amendment)", "url": "https://www.govinfo.gov/content/pkg/USCODE-2024-title49/html/USCODE-2024-title49-subtitleIV-partB-chap147-sec14706.htm"},
            {"title": "49 CFR § 370.3 Filing of claims", "url": "https://www.ecfr.gov/current/title-49/subtitle-B/chapter-III/subchapter-B/part-370/section-370.3"},
            {"title": "49 CFR § 370.5 Acknowledgment of claims", "url": "https://www.ecfr.gov/current/title-49/subtitle-B/chapter-III/subchapter-B/part-370/section-370.5"},
            {"title": "49 CFR § 370.9 Disposition of claims", "url": "https://www.ecfr.gov/current/title-49/subtitle-B/chapter-III/subchapter-B/part-370/section-370.9"},
        ],
    },
}


def _carrier_key(carrier: str | None) -> str | None:
    value = " ".join(str(carrier or "").casefold().replace("&", "and").split())
    if value in {"ups", "united parcel service"} or "ups" in value:
        return "ups"
    if "fedex" in value or "federal express" in value:
        return "fedex"
    if "usps" in value or "postal service" in value or value == "post office":
        return "usps"
    if any(term in value for term in ("ltl", "less than truckload", "freight", "motor carrier")):
        return "ltl"
    return None


def _issue_key(shipment_type: str) -> str:
    value = " ".join(str(shipment_type or "unknown").casefold().replace("_", " ").split())
    if value in {"lost", "not delivered", "undelivered", "missing shipment"}:
        return "lost"
    if value in {"damage", "damaged", "missing contents", "shortage"}:
        return "damage"
    return "unknown"


def carrier_guidance(carrier: str | None, *, shipment_type: str = "damage",
                     international: bool | None = False) -> dict[str, Any]:
    """Return a copy of the matching guidance; unknown services require manual review."""
    key = _carrier_key(carrier)
    issue = _issue_key(shipment_type)
    if key is None:
        return {
            "carrier": carrier or "Unknown carrier",
            "template_id": "manual-review",
            "filing_deadline_days": None,
            "filing_deadline_months": None,
            "filing_deadline_anchor": None,
            "deadline_note": "Carrier or service was not recognized. Confirm the actual carrier contract and filing deadline before relying on a date.",
            "deadline_requires_service_lookup": True,
            "required_evidence": _COMMON_EVIDENCE + ["carrier-specific claim form and service terms confirmed by the customer"],
            "sources": [],
        }
    result = {**_GUIDANCE[key], "required_evidence": list(_GUIDANCE[key]["required_evidence"]),
              "sources": [dict(source) for source in _GUIDANCE[key]["sources"]]}
    result["template_id"] = key
    if key == "fedex" and issue == "lost":
        result["filing_deadline_days"] = None
        result["filing_deadline_months"] = 9
        result["filing_deadline_anchor"] = "shipment_date"
    elif key == "fedex" and issue != "damage":
        result["filing_deadline_days"] = None
        result["filing_deadline_months"] = None
        result["filing_deadline_anchor"] = "shipment_date"
        result["deadline_note"] = "Confirm whether this is damage/missing contents or a lost shipment, and confirm domestic versus international service before calculating a deadline."
        result["deadline_requires_service_lookup"] = True
    elif key == "fedex" and international:
        result["filing_deadline_days"] = 21
        result["filing_deadline_anchor"] = "shipment_date"
    elif key == "fedex" and international is None:
        result["filing_deadline_days"] = None
        result["filing_deadline_months"] = None
        result["deadline_note"] = "Confirm domestic versus international service before calculating the damage/missing-contents deadline."
        result["deadline_requires_service_lookup"] = True
    elif key == "usps" and issue == "lost":
        result["filing_deadline_days"] = None
        result["filing_deadline_anchor"] = "service-specific window from mailing_date"
    elif key == "usps" and issue != "damage":
        result["filing_deadline_days"] = None
        result["filing_deadline_anchor"] = "service-specific window from mailing_date"
        result["deadline_note"] = "Confirm the mail class and issue type; USPS filing windows vary by service."
        result["deadline_requires_service_lookup"] = True
    if key == "usps" and international:
        result["filing_deadline_days"] = None
        result["filing_deadline_anchor"] = "service-specific international mailing window"
        result["deadline_note"] = "Confirm the destination, service, and current international claim rules before calculating a deadline."
        result["deadline_requires_service_lookup"] = True
    elif key == "usps" and international is None:
        result["filing_deadline_days"] = None
        result["filing_deadline_anchor"] = "mailing_date after destination/service confirmation"
        result["deadline_note"] = "Confirm domestic versus international destination and the mail class before calculating a deadline."
        result["deadline_requires_service_lookup"] = True
    return result


def filing_deadline(carrier: str | None, anchor_date: date | str | None, *,
                    shipment_type: str = "damage", international: bool | None = False) -> date | None:
    """Calculate only a source-backed generic window; return None when service lookup is required."""
    guidance = carrier_guidance(carrier, shipment_type=shipment_type, international=international)
    if anchor_date is None:
        return None
    try:
        anchor = anchor_date if isinstance(anchor_date, date) else date.fromisoformat(anchor_date)
    except (TypeError, ValueError):
        return None
    days = guidance["filing_deadline_days"]
    months = guidance["filing_deadline_months"]
    if days is not None:
        return anchor + timedelta(days=days)
    if months is not None:
        month_index = anchor.month - 1 + months
        year = anchor.year + month_index // 12
        month = month_index % 12 + 1
        return date(year, month, min(anchor.day, calendar.monthrange(year, month)[1]))
    return None


def response_schedule(carrier: str | None, filed_on: date | str) -> list[dict[str, str]]:
    """Track dates after customer confirms filing; only LTL has sourced regulatory milestones."""
    filed = filed_on if isinstance(filed_on, date) else date.fromisoformat(filed_on)
    key = _carrier_key(carrier)
    if key != "ltl":
        return []
    milestones = [
        {"due_on": (filed + timedelta(days=30)).isoformat(), "days_after_filing": "30",
         "milestone": "written acknowledgment or disposition", "source": "49 CFR § 370.5"},
        {"due_on": (filed + timedelta(days=120)).isoformat(), "days_after_filing": "120",
         "milestone": "written disposition or carrier status update", "source": "49 CFR § 370.9",
         "repeat_interval_days": "60", "repeat_until": "claim resolved"},
    ]
    return milestones
