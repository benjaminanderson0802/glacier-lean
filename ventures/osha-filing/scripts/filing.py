"""Prepare customer-reviewed OSHA 300A worksheets; never sign or submit them."""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

from ventures.blocks.deadlines import add as add_deadline, due as due_deadlines


def filing_window(on: str | date | None = None) -> str:
    today = date.fromisoformat(on) if isinstance(on, str) else on or date.today()
    start, end = date(today.year, 1, 2), date(today.year, 3, 2)
    return "open" if start <= today <= end else ("upcoming" if today < start else "closed")


def _nonnegative_int(value: Any, name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(name)
    result = int(value)
    if result < 0 or result != float(value):
        raise ValueError(name)
    return result


def prepare_300a(intake: dict[str, Any], output_dir: str | Path, *, as_of: str | date | None = None) -> dict[str, Any]:
    today = date.fromisoformat(as_of) if isinstance(as_of, str) else as_of or date.today()
    confirm: list[str] = []
    establishment = intake.get("establishment") or {}
    if any(not str(establishment.get(key, "")).strip() for key in ("name", "address", "industry_code")):
        confirm.append("establishment identity and industry")
    log = intake.get("injury_log") or {}
    fields = ("deaths", "days_away", "job_transfer", "other_cases", "days_away_count", "job_transfer_count", "other_days")
    try:
        counts = {key: _nonnegative_int(log.get(key, 0), key) for key in fields}
        hours = _nonnegative_int(intake.get("hours_worked"), "hours_worked")
        employees = _nonnegative_int(intake.get("average_employees"), "average_employees")
        year = _nonnegative_int(intake.get("year"), "year")
        headcount = _nonnegative_int(establishment.get("employees"), "employees")
        if hours <= 0 or employees <= 0 or headcount <= 0 or year < 2000 or year > today.year:
            raise ValueError("plausibility")
        avg_hours = hours / employees
        if avg_hours < 100 or avg_hours > 4000 or employees > max(headcount * 2, 1):
            confirm.append("plausible hours and headcount")
    except (TypeError, ValueError, OverflowError):
        counts = {}
        hours = employees = year = 0
        confirm.append("plausible hours and headcount")
    if intake.get("coverage_confirmed") is not True:
        confirm.append("customer confirmation of OSHA coverage")
    if intake.get("customer_confirmed") is not True:
        confirm.append("customer confirmation")
    if not str(intake.get("executive_name", "")).strip() or not str(intake.get("executive_title", "")).strip():
        confirm.append("executive certification contact")
    result = "match" if not confirm else "uncertain — please check"
    path = None
    if result == "match":
        total_cases = counts["deaths"] + counts["days_away"] + counts["job_transfer"] + counts["other_cases"]
        record = {
            "form": "OSHA 300A annual summary review worksheet",
            "calendar_year": year,
            "establishment": establishment["name"],
            "address": establishment["address"],
            "industry_code": establishment["industry_code"],
            "average_employees": employees,
            "hours_worked": hours,
            "injury_log": counts,
            "total_cases": total_cases,
            "executive_name_for_customer_certification": intake["executive_name"],
            "executive_title": intake["executive_title"],
            "certified": False,
            "submitted": False,
            "posting_period": f"{year + 1}-02-01 through {year + 1}-04-30",
            "instruction": "Customer reviews the OSHA 300A, certifies it, submits through its OSHA ITA account, and posts the signed copy. This worksheet is not a filing confirmation.",
        }
        destination = Path(output_dir)
        destination.mkdir(parents=True, exist_ok=True)
        target = destination / f"osha-300a-{year}-review.json"
        target.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        path = str(target)
        add_deadline(f"osha-annual-{establishment['name']}-{year}", f"{year + 1}-01-02", "0d|30d", f"OSHA 300A filing window for {establishment['name']}")
    return {"result": result, "form_path": path, "customer_must_certify_and_submit": True, "signed": False, "submitted": False, "please_confirm": sorted(set(confirm)), "filing_window": filing_window(today)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--intake", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("--as-of")
    due = sub.add_parser("due")
    due.add_argument("--on")
    args = parser.parse_args(argv)
    if args.action == "prepare":
        result = prepare_300a(json.loads(args.intake.read_text(encoding="utf-8")), args.output, as_of=args.as_of)
    else:
        result = due_deadlines(args.on or date.today())
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if args.action == "due" or result["result"] == "match" else 1


if __name__ == "__main__":
    raise SystemExit(main())
