#!/usr/bin/env python3
"""Build the Chrome Web Store ZIP from the extension's runtime files only."""
from __future__ import annotations

import json
from pathlib import Path
import zipfile

STORE_DIR = Path(__file__).resolve().parent
EXTENSION_DIR = STORE_DIR.parent / "extension"
FILES = ("manifest.json", "popup.html", "popup.css", "popup.js")


def build() -> Path:
    manifest_path = EXTENSION_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("manifest_version") != 3:
        raise SystemExit("Refusing to package a non-MV3 extension")
    version = manifest.get("version", "")
    if not version or any(character not in "0123456789." for character in version):
        raise SystemExit(f"Invalid extension version: {version!r}")

    output = STORE_DIR / f"recall-checker-extension-{version}.zip"
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in FILES:
            source = EXTENSION_DIR / name
            if not source.is_file():
                raise SystemExit(f"Missing extension runtime file: {source}")
            archive.write(source, arcname=name)
    return output


if __name__ == "__main__":
    print(build())
