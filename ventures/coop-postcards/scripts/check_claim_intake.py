"""Print the claim checklist for the next local intake; never opens a portal."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workflow import check_claim


def main() -> int:
    path = Path(os.environ.get("GLACIER_HOME", Path.home() / ".glacier")) / "ventures/coop-postcards/intake/claim.json"
    if not path.exists():
        print(json.dumps({"status": "idle", "detail": "No co-op claim intake is waiting; no action taken."}))
        return 0
    record = json.loads(path.read_text(encoding="utf-8"))
    claim_id = str(record.get("claim_id", ""))
    if not claim_id or not claim_id.replace("-", "").replace("_", "").isalnum():
        print(json.dumps({"verdict": "uncertain", "filing_ready": False, "issues": ["a stable claim_id is required"]}))
        return 1
    marker = Path(os.environ.get("GLACIER_HOME", Path.home() / ".glacier")) / "ventures/coop-postcards/claim-attempts" / f"{claim_id}.attempted"
    if marker.exists():
        print(json.dumps({"status": "held", "detail": "This claim was already attempted; review its brand portal status before retrying."}))
        return 1
    result = check_claim(record.get("fields", {}), record.get("rules", {}),
                         evidence_documents=record.get("evidence_documents", []), claim_id=claim_id)
    source_notes = []
    for source in result.get("sources", []):
        field_rows = source.get("fields", {})
        source_notes.append({"document": Path(source["document"]).name,
                             "fields_read": [f"{name} (page {field.get('page')})" if field.get("page") else str(name)
                                             for name, field in field_rows.items()]})
    print(json.dumps({"dealer": record.get("dealer_label", "dealer"), "claim_id": claim_id,
                      "evidence_sources": source_notes, "readiness": result["verdict"],
                      "filing_ready": result["filing_ready"], "issues": result["issues"],
                      "reminders": result.get("reminders", []), "rules_check": result.get("rules_check")}, indent=2))
    return 0 if result["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
