#!/usr/bin/env python3
"""Run the committed labeled recall benchmark against a local NHTSA feed snapshot."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ventures.recall_checker import match_items

BENCH = Path(__file__).resolve().parent
DATASET = BENCH / "recall_benchmark.csv"


def evaluate(cases: list[dict[str, str]], recalls: list[dict[str, Any]], *, as_of: str) -> dict[str, Any]:
    results = []
    items = [{key: case[key] for key in ("brand", "model", "model_year")} for case in cases]
    verdicts = match_items(items, recalls, as_of=as_of)
    for case, verdict in zip(cases, verdicts):
        positive = case["label"] == "recalled"
        matched = verdict["result"] == "match"
        results.append({
            "case_id": case["case_id"],
            "label": case["label"],
            "brand": case["brand"],
            "model": case["model"],
            "model_year": case["model_year"],
            "expected": case["expected"],
            "result": verdict["result"],
            "recall_number": case.get("recall_number", ""),
            "false_negative": positive and not matched,
            "false_no_match": positive and verdict["result"].startswith("no match found"),
            "false_positive": not positive and matched,
            "matched_recall_numbers": [row["recall_number"] for row in verdict["recalls"]],
            "official_url": case["source_url"],
        })

    positives = [row for row in results if row["label"] == "recalled"]
    negatives = [row for row in results if row["label"] == "clean"]
    true_positive = sum(row["result"] == "match" for row in positives)
    false_positive = sum(row["result"] == "match" for row in negatives)
    false_negative = len(positives) - true_positive
    false_no_match = sum(row["false_no_match"] for row in positives)
    clean_no_match = sum(row["result"].startswith("no match found") for row in negatives)
    clean_uncertain = sum(row["result"] == "uncertain — please check" for row in negatives)
    recalled_uncertain = sum(row["result"] == "uncertain — please check" for row in positives)
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / len(positives) if positives else 0.0
    return {
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "as_of": as_of,
        "dataset": str(DATASET.relative_to(ROOT)),
        "counts": {"cases": len(results), "recalled": len(positives), "clean": len(negatives), "true_positive": true_positive, "false_positive": false_positive, "false_negative": false_negative, "false_no_match": false_no_match, "clean_no_match": clean_no_match, "clean_uncertain": clean_uncertain, "recalled_uncertain": recalled_uncertain},
        "precision": precision,
        "recall": recall,
        "false_no_match_rate_on_recalled": false_no_match / len(positives) if positives else 0.0,
        "within_at_most_one_percent_false_no_match_gate": bool(positives) and false_no_match / len(positives) <= 0.01,
        "false_negatives": [row for row in results if row["false_negative"]],
        "false_positives": [row for row in results if row["false_positive"]],
        "uncertain_cases": [row for row in results if row["result"] == "uncertain — please check"],
        "cases": results,
    }


def load_cases(path: Path = DATASET) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        cases = list(csv.DictReader(handle))
    if len(cases) != 1000 or sum(row["label"] == "recalled" for row in cases) != 500 or sum(row["label"] == "clean" for row in cases) != 500:
        raise ValueError("benchmark CSV must contain exactly 500 recalled and 500 clean cases")
    return cases


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=BENCH / "results.json")
    parser.add_argument("--as-of", default=datetime.now(timezone.utc).date().isoformat())
    args = parser.parse_args()
    from ventures.blocks.feeds import query

    recalls = query("nhtsa_recalls")
    if not recalls:
        raise SystemExit("No NHTSA recall snapshot in GLACIER_HOME; sync nhtsa_recalls first.")
    result = evaluate(load_cases(), recalls, as_of=args.as_of)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key not in {"cases", "false_negatives", "false_positives", "uncertain_cases"}}, ensure_ascii=False, indent=2))
    print(f"false_negatives={json.dumps(result['false_negatives'], ensure_ascii=False)}")
    return 0 if result["within_at_most_one_percent_false_no_match_gate"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
