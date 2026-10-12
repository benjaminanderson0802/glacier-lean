"""Send a previously approved postcard only through Lob's test API."""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workflow import send_postcard_file


def _secret(name: str) -> str:
    home = Path(os.environ.get("GLACIER_HOME", Path.home() / ".glacier"))
    try:
        saved = json.loads((home / "secret_names.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return ""
    if name not in saved:
        return ""
    backend = str(Path(__file__).resolve().parents[3] / "glacier/backend")
    if backend not in sys.path:
        sys.path.insert(0, backend)
    from secrets_store import resolve
    try:
        return resolve("{secret:" + name + "}") or ""
    except ValueError:
        return ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--approval", required=True)
    parser.add_argument("--record", default=str(Path(os.environ.get("GLACIER_HOME", Path.home() / ".glacier")) / "ventures/coop-postcards/intake/route-card.json"))
    args = parser.parse_args()
    if not args.approval.strip():
        raise SystemExit("A Glacier approval ID is required.")
    key = _secret("lob_test_api_key")
    if key and not key.startswith("test_"):
        raise SystemExit("Only a Lob test_ key is allowed; no postcard was sent.")
    os.environ["LOB_API_KEY"] = key
    if key:
        record = json.loads(Path(args.record).read_text(encoding="utf-8"))
        campaign_id = str(record.get("campaign_id", ""))
        if not campaign_id or not campaign_id.replace("-", "").replace("_", "").isalnum():
            raise SystemExit("A stable campaign_id is required to prevent duplicate mail.")
        home = Path(os.environ.get("GLACIER_HOME", Path.home() / ".glacier"))
        marker_dir = home / "ventures/coop-postcards/mail-attempts"
        marker_dir.mkdir(parents=True, exist_ok=True)
        marker = marker_dir / f"{campaign_id}.attempted"
        try:
            with marker.open("x", encoding="utf-8") as stream:
                stream.write("attempted\n")
        except FileExistsError:
            raise SystemExit("This campaign_id was already attempted; check Lob before any retry.") from None
    result = send_postcard_file(args.record)
    print(json.dumps({"approval_id": args.approval, **result}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
