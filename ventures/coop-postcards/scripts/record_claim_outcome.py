"""Record a customer-reported co-op portal outcome for retry control."""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workflow import record_claim_outcome


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claim-id", required=True)
    parser.add_argument("--outcome", required=True, choices=("accepted", "rejected"))
    parser.add_argument("--reason", default="", help="required when rejected")
    args = parser.parse_args()
    state_dir = Path(os.environ.get("GLACIER_HOME", Path.home() / ".glacier")) / "ventures/coop-postcards/claim-attempts"
    state = record_claim_outcome(args.claim_id, args.outcome, state_dir, reason=args.reason)
    print(json.dumps(state, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
