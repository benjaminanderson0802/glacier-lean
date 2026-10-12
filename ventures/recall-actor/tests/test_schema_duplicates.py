from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AssertionError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


class SchemaUniquenessTests(unittest.TestCase):
    def test_actor_input_schema_has_no_duplicate_keys(self):
        json.loads((ROOT / ".actor" / "input_schema.json").read_text(encoding="utf-8"), object_pairs_hook=unique_object)

    def test_extension_keeps_local_default_and_only_requested_remote_host(self):
        manifest = json.loads((ROOT.parent / "recall-checker" / "extension" / "manifest.json").read_text(encoding="utf-8"))
        popup = (ROOT.parent / "recall-checker" / "extension" / "popup.html").read_text(encoding="utf-8")
        script = (ROOT.parent / "recall-checker" / "extension" / "popup.js").read_text(encoding="utf-8")
        self.assertEqual(manifest["permissions"], ["activeTab", "scripting", "storage"])
        self.assertEqual(manifest["host_permissions"], ["http://127.0.0.1:8765/*", "https://api.apify.com/*"])
        self.assertIn('<option value="local">', popup)
        self.assertIn('"check-mode": "local"', script)
        self.assertIn("run-sync-dataset", script)


if __name__ == "__main__":
    unittest.main()
