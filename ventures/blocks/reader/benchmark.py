"""Measure field agreement and extraction accuracy on the public labeled set."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from . import read_document


def _normal(value: Any) -> str | None:
    if value is None:
        return None
    return " ".join(str(value).split()).casefold() or None


def run(manifest_path: str | Path) -> dict[str, Any]:
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    base = manifest_path.parent
    total = agreed = correct = labeled_values = 0
    reports = []
    for document in manifest["documents"]:
        path = base / document["file"]
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        output = read_document(path, document.get("schema"))
        fields = output["fields"]
        row = {"id": document["id"], "sha256": actual_hash, "fields": {}}
        for label in document["labels"]:
            key, expected = label["field"], label["value"]
            field = fields.get(key, {"value": None, "page": None, "confidence": 0, "uncertain": True})
            total += 1
            matched = not field["uncertain"]
            agreed += int(matched)
            if expected is not None:
                labeled_values += 1
                correct += int(_normal(field["value"]) == _normal(expected))
            row["fields"][key] = {
                "expected": expected,
                "actual": field["value"],
                "page": field["page"],
                "confidence": field["confidence"],
                "uncertain": field["uncertain"],
                "matches_label": expected is None or _normal(field["value"]) == _normal(expected),
            }
        reports.append(row)
    agreement = agreed / total if total else 0.0
    accuracy = correct / labeled_values if labeled_values else 0.0
    result = {"agreement": agreement, "agreement_percent": round(agreement * 100, 2),
              "labeled_value_accuracy": accuracy,
              "labeled_value_accuracy_percent": round(accuracy * 100, 2),
              "fields": total, "known_value_fields": labeled_values, "documents": reports}
    print(json.dumps(result, indent=2))
    if agreement < 0.95 or accuracy < 0.95:
        raise SystemExit(1)
    return result


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "ventures/blocks/reader/samples/manifest.json")
