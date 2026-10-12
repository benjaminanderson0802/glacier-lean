#!/usr/bin/env python3
"""Build the fixed 500/500 benchmark from NHTSA's official recall and vPIC data."""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlencode

import requests

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

NHTSA_RECALLS = "https://static.nhtsa.gov/odi/ffdd/rcl/FLAT_RCL_POST_2010.zip"
VPIC_ROOT = "https://vpic.nhtsa.dot.gov/api/vehicles"
USER_AGENT = "Glacier recall benchmark/1.0 (official NHTSA public data; polite research client)"
MAKES = (
    "Acura", "Audi", "BMW", "Buick", "Cadillac", "Chevrolet", "Chrysler", "Dodge", "Ford", "GMC",
    "Honda", "Hyundai", "Infiniti", "Jeep", "Kia", "Lexus", "Mazda", "Mercedes-Benz", "MINI", "Mitsubishi",
    "Nissan", "Polestar", "Ram", "Rivian", "Subaru", "Tesla", "Toyota", "Volkswagen", "Volvo",
)
YEARS = (2026, 2025, 2024)
OUTPUT = Path(__file__).resolve().parent / "recall_benchmark.csv"
FIELDS = ("case_id", "label", "brand", "model", "model_year", "expected", "recall_number", "source_date", "source_url", "catalog_url", "label_method", "doubt")


def norm(value: object) -> str:
    return "".join(re.findall(r"[a-z0-9]", str(value or "").casefold()))


def recall_key(data: dict) -> tuple[str, str, str]:
    return (norm(data.get("MAKETXT")), norm(data.get("MODELTXT")), norm(data.get("YEARTXT")))


def fetched_json(session: requests.Session, url: str, *, params: dict | None = None, allow_empty_400: bool = False) -> dict:
    response = session.get(url, params=params, timeout=(8, 30))
    if allow_empty_400 and response.status_code == 400:
        value = response.json()
        if isinstance(value, dict) and value.get("Count") == 0 and value.get("results") == []:
            return value
    response.raise_for_status()
    value = response.json()
    if not isinstance(value, dict):
        raise ValueError(f"Unexpected NHTSA response from {response.url}")
    return value


def make_cases(recall_rows: list[dict], *, today: str, catalog_makes: tuple[str, ...] = MAKES) -> list[dict[str, str]]:
    positive_by_vehicle: dict[tuple[str, str, str], dict] = {}
    for row in recall_rows:
        data = row.get("data", {})
        key = recall_key(data)
        if not all(key) or not re.fullmatch(r"\d{4}", str(data.get("YEARTXT", ""))):
            continue
        if int(data["YEARTXT"]) < 2010:
            continue
        positive_by_vehicle.setdefault(key, row)
    positive_keys = sorted(positive_by_vehicle, key=lambda key: hashlib.sha256("|".join(key).encode()).hexdigest())[:500]
    if len(positive_keys) < 500:
        raise ValueError(f"NHTSA snapshot contains only {len(positive_keys)} usable recalled model-year items")

    cases: list[dict[str, str]] = []
    for index, key in enumerate(positive_keys, 1):
        row = positive_by_vehicle[key]
        data = row["data"]
        campaign = str(data.get("CAMPNO", "")).strip()
        date_raw = str(data.get("RCDATE", "")).strip()
        source_date = f"{date_raw[:4]}-{date_raw[4:6]}-{date_raw[6:8]}" if re.fullmatch(r"\d{8}", date_raw) else today
        cases.append({
            "case_id": f"R{index:03d}", "label": "recalled", "brand": str(data["MAKETXT"]).strip(),
            "model": str(data["MODELTXT"]).strip(), "model_year": str(data["YEARTXT"]).strip(), "expected": "match",
            "recall_number": campaign or str(data.get("RECORD_ID", "")), "source_date": source_date,
            "source_url": f"https://api.nhtsa.gov/recalls/campaignNumber?campaignNumber={quote(campaign)}" if campaign else NHTSA_RECALLS,
            "catalog_url": NHTSA_RECALLS,
            "label_method": "Exact make, model and year appear in NHTSA's current official recall flat file.",
            "doubt": "Campaign applies only to the affected vehicles/configurations stated in the official notice; this benchmark labels the listed make/model/year cohort as recalled.",
        })

    recalled = set(positive_by_vehicle)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    clean_rows: dict[tuple[str, str, str], tuple[str, str, str]] = {}
    last_request = 0.0
    # vPIC confirms each candidate is a real NHTSA catalog model. Absence from
    # the complete NHTSA recall flat file defines a snapshot-clean candidate.
    for year in YEARS:
        for make in catalog_makes:
            elapsed = time.monotonic() - last_request
            if elapsed < 0.2:
                time.sleep(0.2 - elapsed)
            url = f"{VPIC_ROOT}/GetModelsForMakeYear/make/{quote(make, safe='')}/modelyear/{year}"
            payload = fetched_json(session, url, params={"format": "json"})
            last_request = time.monotonic()
            models = payload.get("Results", [])
            if not isinstance(models, list):
                raise ValueError(f"NHTSA vPIC returned no model list for {make} {year}")
            for entry in models:
                if not isinstance(entry, dict):
                    continue
                actual_make = str(entry.get("Make_Name") or make).strip()
                model = str(entry.get("Model_Name") or "").strip()
                key = (norm(actual_make), norm(model), str(year))
                if model and key not in recalled:
                    catalog_url = url + "?format=json"
                    clean_rows.setdefault(key, (actual_make, model, catalog_url))
            if len(clean_rows) >= 1500:
                break
        if len(clean_rows) >= 1500:
            break
    if len(clean_rows) < 500:
        raise ValueError(f"NHTSA vPIC yielded only {len(clean_rows)} snapshot-clean model-year candidates")

    verified_clean: list[tuple[tuple[str, str, str], str, str, str, str]] = []
    for key, (make, model, catalog_url) in sorted(clean_rows.items(), key=lambda item: hashlib.sha256("|".join(item[0]).encode()).hexdigest()):
        elapsed = time.monotonic() - last_request
        if elapsed < 0.2:
            time.sleep(0.2 - elapsed)
        recall_url = "https://api.nhtsa.gov/recalls/recallsByVehicle"
        query = {"make": make, "model": model, "modelYear": key[2]}
        payload = fetched_json(session, recall_url, params=query, allow_empty_400=True)
        last_request = time.monotonic()
        found = payload.get("results")
        if not isinstance(found, list) or (payload.get("Count") not in (0, len(found))):
            raise ValueError(f"NHTSA returned inconsistent count/results for clean-candidate check: {make} {model} {key[2]}")
        if payload.get("Count") == 0 and not found:
            query_url = recall_url + "?" + urlencode(query)
            verified_clean.append((key, make, model, catalog_url, query_url))
        if len(verified_clean) == 500:
            break
    if len(verified_clean) < 500:
        raise ValueError(f"NHTSA verified only {len(verified_clean)} clean model-year candidates")

    for index, (key, make, model, catalog_url, recall_query_url) in enumerate(verified_clean, 1):
        cases.append({
            "case_id": f"C{index:03d}", "label": "clean", "brand": make,
            "model": model, "model_year": key[2], "expected": "no_match", "recall_number": "",
            "source_date": today, "source_url": recall_query_url, "catalog_url": catalog_url,
            "label_method": "NHTSA vPIC confirms this make/model/year exists; the current complete NHTSA recall flat file has no exact row and the NHTSA recalls-by-vehicle API returned Count=0.",
            "doubt": "This remains a model-year lookup, not a VIN/configuration determination; a newly announced or configuration-limited campaign may change the result. Recheck current NHTSA data before acting.",
        })
    return cases


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--date", default=datetime.now(timezone.utc).date().isoformat())
    args = parser.parse_args()
    from ventures.blocks.feeds import query

    recalls = query("nhtsa_recalls")
    if not recalls:
        raise SystemExit("No live NHTSA recall snapshot in GLACIER_HOME; run: python -m ventures.blocks.feeds.cli sync nhtsa_recalls")
    cases = make_cases(recalls, today=args.date)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(cases)
    print(f"wrote {len(cases)} cases ({sum(row['label'] == 'recalled' for row in cases)} recalled, {sum(row['label'] == 'clean' for row in cases)} clean) to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
