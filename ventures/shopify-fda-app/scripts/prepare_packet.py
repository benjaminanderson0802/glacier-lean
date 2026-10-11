#!/usr/bin/env python3
"""Call the existing FDA packet builder in a short-lived, isolated workspace."""
import base64
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_DIR.parents[1]
SOURCE = REPO_ROOT / "ventures" / "fda-cosmetics" / "scripts" / "listing_prep.py"
spec = importlib.util.spec_from_file_location("glacier_fda_listing_prep", SOURCE)
if spec is None or spec.loader is None:
    raise RuntimeError("Existing FDA packet generator is unavailable")
listing_prep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(listing_prep)

payload = json.load(sys.stdin)
with tempfile.TemporaryDirectory(prefix="glacier-fda-packet-") as output:
    result = listing_prep.prepare_listing(payload, output)
    zip_path = Path(output) / result["spl_zip"] if result.get("spl_zip") else None
    if zip_path and zip_path.is_file():
        result["packetZip"] = {
            "name": zip_path.name,
            "base64": base64.b64encode(zip_path.read_bytes()).decode("ascii"),
        }
    print(json.dumps(result, ensure_ascii=False))
