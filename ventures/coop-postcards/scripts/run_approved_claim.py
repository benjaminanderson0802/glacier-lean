"""Legacy entry point: co-op claim filing is a manual owner action."""
import argparse
import json


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approval", help="legacy Glacier approval ID (not accepted for filing)")
    parser.parse_args(argv)
    print(json.dumps({
        "status": "owner_action_required",
        "detail": "Glacier approval recorded the local draft review only. The dealer must authorize, sign, and submit directly; no portal was opened and no claim was filed.",
        "external_actions": "none",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
