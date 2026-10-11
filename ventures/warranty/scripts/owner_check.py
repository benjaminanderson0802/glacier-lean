"""Run the warranty Jobber → deadline queue → homeowner draft owner check.

Usage from the repository root:
    ~/w/glacier-lean/.venv/bin/python ventures/warranty/scripts/owner_check.py

Jobber OAuth values are resolved from Glacier's OS keychain at request time.
This command performs GraphQL reads only and never sends the displayed drafts.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from ventures.warranty.scripts.warranty import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main(["jobber-preview"]))
