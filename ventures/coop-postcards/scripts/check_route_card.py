"""Check the next route card and render proof files locally."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workflow import check_route_card, render_postcard
from ventures.blocks.mail import landing_pages, verify_address


def main() -> int:
    home = Path(os.environ.get("GLACIER_HOME", Path.home() / ".glacier"))
    path = home / "ventures/coop-postcards/intake/route-card.json"
    if not path.exists():
        print(json.dumps({"status": "idle", "detail": "No route card is waiting; no action taken."}))
        return 0
    card = json.loads(path.read_text(encoding="utf-8"))
    result = check_route_card(card)
    if result["verdict"] != "pass":
        print(json.dumps(result, indent=2))
        return 1
    out = home / "ventures/coop-postcards/proofs"
    out.mkdir(parents=True, exist_ok=True)
    template = '<main><h1>{{dealer_name}}</h1><p>{{town}}</p><p>From {{sender}}</p></main>'
    records = [
        {"id": str(job.get("id") or f"job-{i}"), "dealer_name": job.get("dealer_name", "Your ad here"), "town": card["town"], "sender": card.get("sender", "Glacier Co-op & Street Cards"), "street": job["address"]}
        for i, job in enumerate(card.get("street_jobs", []), 1)
    ] or [{"id": "route-card", "dealer_name": "Your ad here", "town": card["town"], "sender": card.get("sender", "Glacier Co-op & Street Cards"), "street": ""}]
    pages = landing_pages(records, template, output_dir=out / "landing")
    sample = card.get("proof_record") or {"dealer_name": "Your ad here", "town": card["town"], "street": ""}
    front, back = render_postcard(sample)
    (out / "front.html").write_text(front, encoding="utf-8")
    (out / "back.html").write_text(back, encoding="utf-8")
    address_check = verify_address(card.get("to", {}))
    print(json.dumps({**result, "route": card, "address_check": address_check, "front": front, "back": back, "landing_pages": pages}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
