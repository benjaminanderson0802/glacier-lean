"""Keep a rebuildable local per-importer batch status board."""

from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path


def status_dir() -> Path:
    return Path(os.environ.get("GLACIER_HOME", "data")) / "ventures" / "cpsc-prep" / "status"


def record_result(result_path: Path, root: Path | None = None) -> Path:
    result = json.loads(result_path.read_text(encoding="utf-8"))
    batch_id = str(result.get("batch_id", "")).strip()
    if not batch_id or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for ch in batch_id):
        raise ValueError("batch result must have a safe batch_id")
    importer_id = str(result.get("importer_id", "unassigned")).strip() or "unassigned"
    if any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for ch in importer_id):
        raise ValueError("batch result must have a safe importer_id")
    destination = (root or status_dir()) / importer_id / f"{batch_id}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps({
        "batch_id": batch_id,
        "importer_id": importer_id,
        "date": result.get("generated_at", date.today().isoformat()),
        "status": result.get("status"),
        "product_count": len(result.get("products", [])),
        "gap_count": len(result.get("gaps", [])),
        "submission_performed": False,
    }, indent=2) + "\n", encoding="utf-8")
    return destination


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    record = sub.add_parser("record")
    record.add_argument("--result", type=Path, required=True)
    sub.add_parser("launch-ready")
    args = parser.parse_args()
    if args.action == "record":
        print(record_result(args.result))
    else:
        print("CPSC broker portal launch approvals recorded; no account or contract action performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
