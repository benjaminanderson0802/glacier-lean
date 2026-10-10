"""Command entry point for the daily sync flow."""

import json
import sys

from .core import registry, sync, sync_all


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args == ["sync-all"]:
        result = sync_all()
    elif len(args) == 2 and args[0] == "sync":
        result = {args[1]: sync(args[1])}
    elif args == ["list"]:
        print(json.dumps(registry(), indent=2))
        return 0
    else:
        print("usage: python -m ventures.blocks.feeds.cli sync-all | sync SOURCE_ID | list", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return int(any(outcome["alerts"] for outcome in result.values()))


if __name__ == "__main__":
    raise SystemExit(main())
