"""Prepare and submit a dealer-authorized brand claim after a flow approval."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workflow import begin_claim_attempt, check_claim


def _secret(name: str) -> str:
    backend = str(Path(__file__).resolve().parents[3] / "glacier/backend")
    if backend not in sys.path:
        sys.path.insert(0, backend)
    from secrets_store import resolve
    value = resolve("{secret:" + name + "}")
    if not value:
        raise RuntimeError(f"Save {name} in Glacier Settings > Secrets before continuing.")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--approval", required=True)
    parser.add_argument("--input", default=str(Path.home() / ".glacier/ventures/coop-postcards/intake/claim.json"))
    args = parser.parse_args()
    if not args.approval.strip():
        raise SystemExit("A Glacier approval ID is required.")
    record = json.loads(Path(args.input).read_text(encoding="utf-8"))
    claim_id = str(record.get("claim_id", ""))
    if not claim_id or not claim_id.replace("-", "").replace("_", "").isalnum():
        raise SystemExit("A stable claim_id is required to prevent a duplicate filing.")
    readiness = check_claim(record.get("fields", {}), record.get("rules", {}),
                            evidence_documents=record.get("evidence_documents", []), claim_id=claim_id)
    if not readiness["filing_ready"]:
        raise SystemExit(json.dumps(readiness, indent=2))
    from ventures.blocks.filer import prepare, submit
    portal = record["portal"]
    if portal.get("government_agency"):
        raise SystemExit("Government filings must be signed and submitted by the customer; no portal action was taken.")
    home = Path(os.environ.get("GLACIER_HOME", Path.home() / ".glacier"))
    state_dir = home / "ventures/coop-postcards/claim-attempts"
    auth = dict(portal)
    auth["username"] = _secret(portal["username_secret"])
    auth["password"] = _secret(portal["password_secret"])
    fields = {**record["fields"], "dealer": record.get("dealer_label", "dealer")}
    draft = prepare(portal["portal_id"], fields, auth)
    attempt = begin_claim_attempt(claim_id, state_dir)
    confirmation = submit(draft, args.approval)
    print(json.dumps({"status": "submitted", "attempt": attempt["attempts"], "confirmation": confirmation,
                      "next_step": f"Record the customer-reported portal outcome with scripts/record_claim_outcome.py --claim-id {claim_id} --outcome accepted|rejected."}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
