#!/usr/bin/env python3
"""Recall checker feed, batch, and local API commands."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ventures.blocks.feeds import sync
from ventures.recall_checker import SOURCES, check_item, feed_snapshot_problem, generate_pages, process_csv, query_recall_feeds
from fsis_feed import sync_fsis_feed


def home() -> Path:
    return Path(os.environ.get("GLACIER_HOME", "data")).expanduser().resolve() / "ventures" / "recall-checker"


def _page_rows(rows: list[dict]) -> list[dict]:
    """Add direct official record links where a source API omits a page URL."""
    prepared = []
    for row in rows:
        copied = dict(row)
        data = dict(row.get("data") or {})
        source_id = str(row.get("source_id", ""))
        if source_id == "fsis_recalls" and not any(data.get(key) for key in ("RecallURL", "recall_url", "URL", "url", "link", "web_url", "source_url")):
            notice_url = str(data.get("field_recall_url", ""))
            if notice_url.startswith("https://www.fsis.usda.gov/"):
                data["URL"] = notice_url
        elif source_id == "fda_enforcement" and not any(data.get(key) for key in ("URL", "url", "link", "web_url", "source_url")):
            recall_number = str(data.get("recall_number", "")).strip()
            search_field = "recall_number" if recall_number else "event_id"
            record_identifier = recall_number or str(data.get("event_id", "")).strip()
            dataset = str(data.get("_openfda_dataset", "Food")).casefold()
            if record_identifier and dataset in {"food", "drug", "device"}:
                query = urlencode({"search": f'{search_field}:"{record_identifier}"', "limit": 1})
                data["URL"] = f"https://api.fda.gov/{dataset}/enforcement.json?{query}"
        copied["data"] = data
        prepared.append(copied)
    return prepared


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    refresh = commands.add_parser("nightly", help="refresh recall feeds and generate local notice pages")
    refresh.add_argument("--skip-sync", action="store_true")
    refresh.add_argument("--require-complete", action="store_true", help="explicitly require every source before refreshing local pages")
    refresh.add_argument("--limit-pages", type=int, help="generate at most this many pages (for review packets)")
    batch = commands.add_parser("batch", help="check inventory CSV and write a flagged copy")
    batch.add_argument("input", type=Path)
    batch.add_argument("--output", type=Path)
    lookup = commands.add_parser("match", help="check one product from JSON")
    lookup.add_argument("--barcode", default="")
    lookup.add_argument("--brand", default="")
    lookup.add_argument("--model", default="")
    args = parser.parse_args()

    if args.command == "nightly":
        sync_results = {}
        if not args.skip_sync:
            sync_results = {source: sync_fsis_feed() if source == "fsis_recalls" else sync(source) for source in SOURCES}
        rows, missing = query_recall_feeds()
        alerts = {source: value["alerts"] for source, value in sync_results.items() if value.get("alerts")}
        output = home() / "pages"
        freshness_problem = feed_snapshot_problem(rows, missing)
        blocked = bool(missing or alerts or freshness_problem)
        # A partial or alerted feed must never produce fresh pages that could
        # be mistaken for a complete recall snapshot. Route the nonzero result
        # to the flow's durable feed-alert step instead.
        review_order = sorted(_page_rows(rows), key=lambda row: (str(row.get("record_date") or ""), str(row.get("source_id") or ""), str(row.get("record_id") or "")), reverse=True)
        pages = [] if blocked else generate_pages(review_order, output, limit=args.limit_pages)
        result = {"sources": sync_results, "recall_rows": len(rows), "missing_sources": missing, "freshness_problem": freshness_problem, "alerts": alerts, "pages_generated": len(pages), "pages_directory": str(output), "first_fifty_review_required": len(pages) > 0}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if blocked else 0
    elif args.command == "batch":
        rows, missing = query_recall_feeds()
        out = args.output or home() / "outputs" / f"{args.input.stem}-recall-check.csv"
        path = process_csv(args.input, out, rows, as_of=date.today().isoformat(), missing_sources=missing)
        result = {"output": str(path), "missing_sources": missing, "rows_checked": sum(1 for _ in args.input.open(encoding="utf-8-sig")) - 1}
    else:
        result = check_item({"barcode": args.barcode, "brand": args.brand, "model": args.model})
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
