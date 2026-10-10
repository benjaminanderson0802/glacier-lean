#!/usr/bin/env python3
"""Recall checker feed, batch, and local API commands."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ventures.blocks.feeds import sync
from ventures.recall_checker import SOURCES, check_item, generate_pages, process_csv, query_recall_feeds


def home() -> Path:
    return Path(os.environ.get("GLACIER_HOME", "data")).expanduser().resolve() / "ventures" / "recall-checker"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    refresh = commands.add_parser("nightly", help="refresh recall feeds and generate local notice pages")
    refresh.add_argument("--skip-sync", action="store_true")
    refresh.add_argument("--require-complete", action="store_true", help="refuse page refresh if any recall source is missing or alerts")
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
            sync_results = {source: sync(source) for source in SOURCES}
        rows, missing = query_recall_feeds()
        alerts = {source: value["alerts"] for source, value in sync_results.items() if value.get("alerts")}
        output = home() / "pages"
        blocked = bool(missing or alerts)
        pages = [] if (args.require_complete and blocked) else generate_pages(rows, output)
        result = {"sources": sync_results, "recall_rows": len(rows), "missing_sources": missing, "alerts": alerts, "pages_generated": len(pages), "pages_directory": str(output), "first_fifty_review_required": len(pages) > 0}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if args.require_complete and blocked else 0
    elif args.command == "batch":
        rows, missing = query_recall_feeds()
        out = args.output or home() / "outputs" / f"{args.input.stem}-recall-check.csv"
        path = process_csv(args.input, out, rows, as_of=date.today().isoformat())
        result = {"output": str(path), "missing_sources": missing, "rows_checked": sum(1 for _ in args.input.open(encoding="utf-8-sig")) - 1}
    else:
        result = check_item({"barcode": args.barcode, "brand": args.brand, "model": args.model})
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
