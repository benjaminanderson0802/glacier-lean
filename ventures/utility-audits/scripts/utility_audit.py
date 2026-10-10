"""Customer-entered estimate and unsigned Indiana ST-200R preparation data."""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import argparse
import json
import os
from pathlib import Path
from typing import Any


RULE_SOURCE = "Indiana DOR Utility Sales Tax Exemption, Sales Tax Information Bulletins #11 and #29"
CENT = Decimal("0.01")


def _amount(value: Any, field: str) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{field} must be a non-negative number") from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError(f"{field} must be a non-negative number")
    return amount


def _months(rows: Any, *, kind: str) -> dict[str, dict[str, Decimal]]:
    if not isinstance(rows, list):
        raise ValueError(f"{kind} must be a list of monthly records")
    result: dict[str, dict[str, Decimal]] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"{kind}[{index}] must be an object")
        period = row.get("period")
        if not isinstance(period, str) or len(period) != 7 or period[4] != "-":
            raise ValueError(f"{kind}[{index}].period must use YYYY-MM")
        try:
            date.fromisoformat(f"{period}-01")
        except ValueError as exc:
            raise ValueError(f"{kind}[{index}].period must be a real calendar month") from exc
        if period in result:
            raise ValueError(f"duplicate {kind} period: {period}")
        if kind == "sales_months":
            category_keys = ("prepared_food_line1", "prepared_food_line2", "prepared_food_line3")
            categories = [_amount(row[key], key) for key in category_keys if key in row]
            if categories and len(categories) != 3:
                raise ValueError("provide all three ST-200R prepared-food categories or none")
            prepared = sum(categories, Decimal(0)) if categories else _amount(row.get("prepared_food_receipts"), "prepared_food_receipts")
            total = _amount(row.get("total_receipts"), "total_receipts")
            if total == 0 and prepared != 0:
                raise ValueError("prepared food receipts cannot exceed zero total receipts")
            if prepared > total:
                raise ValueError("prepared food receipts cannot exceed total receipts")
            result[period] = {"prepared": prepared, "total": total}
            if categories:
                result[period].update({f"line{index + 1}": amount for index, amount in enumerate(categories)})
        else:
            result[period] = {"tax": _amount(row.get("electricity_sales_tax"), "electricity_sales_tax")}
    return result


def _empty_estimate() -> dict[str, Any]:
    return {
        "estimated_annual_savings": None,
        "basis": "50% of reported electricity sales tax",
        "estimate_type": "future annual savings after approval",
        "currency": "USD",
    }


def _consecutive_months(periods: list[str]) -> bool:
    ordinals = []
    for period in periods:
        year, month = (int(part) for part in period.split("-"))
        ordinals.append(year * 12 + month)
    return len(ordinals) == 12 and all(right == left + 1 for left, right in zip(ordinals, ordinals[1:]))


def _rate_check(data: dict[str, Any], today: str) -> dict[str, Any]:
    if str(data.get("state", "")).strip().upper() != "IN":
        return {
            "result": "uncertain — please check",
            "as_of": today,
            "estimated_annual_savings": None,
            "availability": "uncertain — please check",
            "detail": "The rate comparison is limited to customer-entered Indiana flat-rate plans.",
        }
    comparison = data.get("rate_comparison")
    if not isinstance(comparison, dict):
        return {
            "result": "uncertain — please check",
            "as_of": today,
            "estimated_annual_savings": None,
            "availability": "uncertain — please check",
            "detail": "Enter the utility's published flat rates for both plans, annual kWh, fixed monthly charges, and source links.",
        }
    annual_kwh = _amount(comparison.get("annual_kwh"), "annual_kwh")
    if annual_kwh <= 0:
        raise ValueError("annual_kwh must be greater than zero")
    plans: dict[str, dict[str, Any]] = {}
    for key in ("current_plan", "alternative_plan"):
        plan = comparison.get(key)
        if not isinstance(plan, dict) or not str(plan.get("name", "")).strip():
            return {
                "result": "uncertain — please check",
                "as_of": today,
                "estimated_annual_savings": None,
                "availability": "uncertain — please check",
                "detail": "Both named plans and their published rate details are needed for a comparison.",
            }
        source_url = str(plan.get("source_url", ""))
        if not source_url.startswith("https://"):
            return {
                "result": "uncertain — please check",
                "as_of": today,
                "estimated_annual_savings": None,
                "availability": "uncertain — please check",
                "detail": "Provide an HTTPS link to the utility's published rate source for each plan.",
            }
        rate = _amount(plan.get("rate_per_kwh"), f"{key}.rate_per_kwh")
        fixed = _amount(plan.get("monthly_fixed_charge"), f"{key}.monthly_fixed_charge")
        annual_cost = (annual_kwh * rate + fixed * Decimal(12)).quantize(CENT, rounding=ROUND_HALF_UP)
        plans[key] = {"name": str(plan["name"]), "source_url": source_url, "estimated_annual_cost": annual_cost}
    savings = plans["current_plan"]["estimated_annual_cost"] - plans["alternative_plan"]["estimated_annual_cost"]
    outcome = "match" if savings > 0 else f"no match found in customer-provided Indiana published flat-rate options as of {today}"
    return {
        "result": outcome,
        "as_of": today,
        "annual_kwh": float(annual_kwh),
        "current_plan": {**plans["current_plan"], "estimated_annual_cost": float(plans["current_plan"]["estimated_annual_cost"])},
        "alternative_plan": {**plans["alternative_plan"], "estimated_annual_cost": float(plans["alternative_plan"]["estimated_annual_cost"])},
        "estimated_annual_savings": float(savings),
        "availability": "uncertain — please check",
        "detail": "Scenario uses customer-entered flat rates and links; links and tariff terms are not fetched or validated. It excludes demand charges, taxes, riders, and other tariff charges. Confirm availability and the complete tariff with the utility.",
    }


def calculate_audit(data: dict[str, Any], *, as_of: date | None = None) -> dict[str, Any]:
    """Estimate Indiana's restaurant electricity exemption from supplied records.

    The calculator never decides legal eligibility. It checks customer-confirmed
    statewide threshold totals and prepares a selected-meter form-field draft only.
    """
    if not isinstance(data, dict):
        raise ValueError("input must be an object")
    today = (as_of or date.today()).isoformat()
    rate_check = _rate_check(data, today)
    state = str(data.get("state", "")).strip().upper()
    if state != "IN":
        return {
            "result": f"no match found in Indiana DOR restaurant electricity rule as of {today}",
            "as_of": today,
            "rule_source": RULE_SOURCE,
            "detail": "This calculator only covers Indiana restaurant electricity applications.",
            "estimate": _empty_estimate(),
            "rate_check": rate_check,
            "state_form_draft": None,
            "next_step": "Use a calculator for the business's state.",
        }

    sales = _months(data.get("sales_months", []), kind="sales_months")
    bills = _months(data.get("electric_bills", []), kind="electric_bills")
    if not data.get("customer_confirmed_receipts") or data.get("single_electric_meter") is not True:
        return _uncertain(today, "Confirm the receipt figures and whether this electricity is supplied through one meter.", rate_check)
    if len(sales) < 12 or len(bills) < 12:
        return _uncertain(today, "At least 12 months of sales figures and electricity bills are needed for ST-200R preparation.", rate_check)
    if not _consecutive_months(sorted(sales)[-12:]) or not _consecutive_months(sorted(bills)[-12:]):
        return _uncertain(today, "The submitted sales figures and electricity bills must each cover 12 consecutive calendar months.", rate_check)

    statewide = data.get("statewide_sales_test")
    if (
        not isinstance(statewide, dict)
        or statewide.get("all_indiana_establishments_included") is not True
        or statewide.get("customer_confirmed") is not True
        or not statewide.get("tax_year")
    ):
        return _uncertain(today, "Confirm the DOR 75% test for the seller's annual figures across all Indiana establishments.", rate_check)
    statewide_prepared = _amount(statewide.get("prepared_food_sales"), "statewide prepared_food_sales")
    statewide_total = _amount(statewide.get("total_food_sales"), "statewide total_food_sales")
    if statewide_total <= 0 or statewide_prepared > statewide_total:
        return _uncertain(today, "The statewide prepared-food and total-food sales figures need customer review.", rate_check)
    if statewide_prepared / statewide_total < Decimal("0.75"):
        return {
            "result": f"no match found in Indiana DOR restaurant electricity rule as of {today}",
            "as_of": today,
            "rule_source": RULE_SOURCE,
            "detail": "Customer-confirmed annual statewide prepared-food sales are below Indiana's 75% threshold.",
            "statewide_tax_year": str(statewide["tax_year"]),
            "statewide_receipt_ratio": float(statewide_prepared / statewide_total),
            "estimate": _empty_estimate(),
            "rate_check": rate_check,
            "state_form_draft": None,
            "next_step": "Ask an Indiana tax professional if another utility exemption may apply.",
        }

    total_receipts = sum((row["total"] for row in sales.values()), Decimal(0))
    prepared_receipts = sum((row["prepared"] for row in sales.values()), Decimal(0))
    if total_receipts <= 0:
        return _uncertain(today, "The provided sales period has no total receipts to compare.", rate_check)
    # Use the latest 12 overlapping months to match ST-200R's minimum record period.
    overlap = sorted(set(sales) & set(bills))[-12:]
    if not _consecutive_months(overlap):
        return _uncertain(today, "The sales records and bills must cover the same 12 monthly periods.", rate_check)
    prepared_12 = sum((sales[period]["prepared"] for period in overlap), Decimal(0))
    total_12 = sum((sales[period]["total"] for period in overlap), Decimal(0))
    if total_12 <= 0:
        return _uncertain(today, "The provided ST-200R period has no total receipts to compare.", rate_check)

    annual_savings = (sum((bills[period]["tax"] for period in overlap), Decimal(0)) * Decimal("0.50")).quantize(CENT, rounding=ROUND_HALF_UP)
    fields = {
        "legal_name": data.get("legal_name", ""),
        "telephone": data.get("telephone", ""),
        "legal_address": data.get("legal_address", ""),
        "dba_name": data.get("dba_name", data.get("business_name", "")),
        "meter_location_address": data.get("meter_location_address", ""),
        "billing_name": data.get("utility_account_name", ""),
        "franchise_name": data.get("franchise_name", ""),
        "indiana_taxpayer_id": data.get("indiana_taxpayer_id", ""),
        "location_number": data.get("location_number", ""),
        "fein": data.get("fein", ""),
        "utility_company": data.get("utility_company", ""),
        "naics_code": data.get("naics_code", ""),
        "meter_number": data.get("meter_number", ""),
        "utility_account_number": data.get("utility_account_number", ""),
        "hours_per_day": data.get("hours_per_day", ""),
        "days_per_week": data.get("days_per_week", ""),
        "weeks_per_year": data.get("weeks_per_year", ""),
        "operation_overview": data.get("operation_overview", ""),
        "section_f_prepared_food_receipts": float(prepared_12),
        "section_f_total_receipts": float(total_12),
        "section_f_prepared_food_percentage": round(float(prepared_12 / total_12) * 100, 2),
        "section_f_prepared_food_line1": float(sum((sales[period].get("line1", Decimal(0)) for period in overlap), Decimal(0))) if all("line1" in sales[period] for period in overlap) else None,
        "section_f_prepared_food_line2": float(sum((sales[period].get("line2", Decimal(0)) for period in overlap), Decimal(0))) if all("line2" in sales[period] for period in overlap) else None,
        "section_f_prepared_food_line3": float(sum((sales[period].get("line3", Decimal(0)) for period in overlap), Decimal(0))) if all("line3" in sales[period] for period in overlap) else None,
        "single_electric_meter": True,
        "supporting_periods": overlap,
        "signature": "",
        "printed_name": "",
        "email": "",
        "date": "",
    }
    missing_fields = [name for name, value in fields.items() if value == "" and name not in {"franchise_name", "location_number", "fein"}]
    if any(fields[f"section_f_prepared_food_line{line}"] is None for line in (1, 2, 3)):
        missing_fields.append("section_f_prepared_food_line1-line3: supply the ST-200R category breakdown")
    return {
        "result": "match",
        "as_of": today,
        "rule_source": RULE_SOURCE,
        "detail": "Customer-confirmed annual statewide totals meet the numeric threshold; the selected meter's form data is prepared separately. Indiana DOR decides the application.",
        "location_form_receipt_ratio": float(prepared_12 / total_12),
        "statewide_tax_year": str(statewide["tax_year"]),
        "statewide_receipt_ratio": float(statewide_prepared / statewide_total),
        "estimate": {
            **_empty_estimate(),
            "estimated_annual_savings": float(annual_savings),
            "reported_annual_electricity_sales_tax": float(sum((bills[period]["tax"] for period in overlap), Decimal(0))),
        },
        "rate_check": rate_check,
        "state_form_draft": {
            "form": "ST-200R",
            "title": "Electric Utility Sales Tax Exemption Application for Restaurants",
            "source_url": "https://www.in.gov/dor/tax-forms/business/sales-tax-forms/index.html",
            "fields": fields,
            "missing_fields": missing_fields,
            "attachments_to_add": ["12 months of utility bills showing the billing name and meter details"],
            "signed": False,
            "submitted": False,
            "note": "Field preparation only. Customer must review, complete missing details, sign, attach bills, and submit to Indiana DOR.",
        },
        "next_step": "Customer reviews the ST-200R draft, completes missing fields, signs it, attaches bills, and submits it to Indiana DOR.",
    }


def _uncertain(today: str, detail: str, rate_check: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "result": "uncertain — please check",
        "as_of": today,
        "rule_source": RULE_SOURCE,
        "detail": detail,
        "estimate": _empty_estimate(),
        "rate_check": rate_check or {
            "result": "uncertain — please check",
            "as_of": today,
            "estimated_annual_savings": None,
            "availability": "uncertain — please check",
            "detail": "Provide published flat-rate options to compare.",
        },
        "state_form_draft": None,
        "next_step": "Customer checks the missing records and confirms them before preparing an application.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("calculate", choices=["calculate"])
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    result = calculate_audit(data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    try:
        os.chmod(args.output, 0o600)
    except OSError:
        pass
    print(json.dumps({"result": result["result"], "output": str(args.output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
