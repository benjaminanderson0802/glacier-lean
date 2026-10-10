import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ventures.blocks.mail import (
    add_to_suppression,
    check_outreach,
    landing_pages,
    postcard,
    verify_address,
)


class MailAcceptanceTests(unittest.TestCase):
    def test_no_key_is_render_only_and_produces_print_proof(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"LOB_API_KEY": ""}):
            result = postcard(
                "<main>Front: Glacier Signs</main>",
                "<main>Back: call 555-0101</main>",
                {"name": "Example Shop", "address": "100 Main St", "city": "Madison", "state": "WI", "zip": "53703"},
                {"name": "Glacier Signs", "address": "200 Lake St", "city": "Madison", "state": "WI", "zip": "53703"},
                output_dir=tmp,
            )
            self.assertEqual(result["status"], "render_only")
            self.assertTrue(Path(result["proof_pdf"]).is_file())
            self.assertGreater(Path(result["proof_pdf"]).stat().st_size, 500)
            self.assertTrue(Path(result["front_html"]).is_file())
            self.assertTrue(Path(result["back_html"]).is_file())

    def test_outreach_rules_and_suppression_prevent_send(self):
        record = {"id": "prospect-1", "address": "100 Main St", "sender": "Glacier Signs", "fields": {"assessed_value": 240000}}
        self.assertEqual(check_outreach(record, "<p>Glacier Signs — your property was listed at $240,000.</p>")["verdict"], "pass")
        self.assertEqual(check_outreach(record, "<p>Official government notice. Seal</p>")["verdict"], "fail")
        with tempfile.TemporaryDirectory() as tmp:
            add_to_suppression("100 Main St, Madison WI 53703", path=Path(tmp) / "suppression.txt")
            blocked = check_outreach(record, "<p>Glacier Signs</p>", suppression_path=Path(tmp) / "suppression.txt")
            self.assertEqual(blocked["verdict"], "fail")
            self.assertIn("suppressed", blocked["reason"].lower())

    def test_missing_address_is_uncertain_and_test_key_is_required(self):
        self.assertEqual(verify_address({})["verdict"], "uncertain")
        with patch.dict(os.environ, {"LOB_API_KEY": "live_never-send"}):
            with self.assertRaisesRegex(ValueError, "test"):
                postcard("front", "back", {"address": "a"}, {"name": "Sender"})

    def test_landing_pages_are_distinct_and_show_real_source_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = landing_pages(
                [
                    {"id": "parcel-1", "owner": "A. Rivera", "assessed_value": 240000},
                    {"id": "parcel-2", "owner": "B. Chen", "assessed_value": 310000},
                ],
                "<h1>{{owner}}</h1><p>Assessed at ${{assessed_value}}</p>",
                output_dir=tmp,
            )
            first = (Path(site) / "parcel-1.html").read_text()
            second = (Path(site) / "parcel-2.html").read_text()
            self.assertIn("A. Rivera", first)
            self.assertIn("240000", first)
            self.assertIn("B. Chen", second)
            self.assertIn("310000", second)
            self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
