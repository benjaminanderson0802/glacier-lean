import unittest
import json
from datetime import date
from pathlib import Path
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.utility_audit import calculate_audit


class UtilityAuditAcceptanceTests(unittest.TestCase):
    def test_eligible_indiana_restaurant_gets_half_electricity_tax_estimate_and_unsigned_draft(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.geturl.return_value = "https://utility.example/rates"
        response.read.return_value = b"published tariff fixture"
        with patch("scripts.utility_audit.urllib.request.urlopen", return_value=response):
            result = calculate_audit({
            "state": "IN",
            "customer_confirmed_receipts": True,
            "single_electric_meter": True,
            "business_name": "Sample Kitchen",
            "utility_account_name": "Sample Kitchen LLC",
            "utility_account_number": "12345",
            "sales_months": [
                {"period": f"2026-{month:02}", "prepared_food_line1": 2000, "prepared_food_line2": 3000,
                 "prepared_food_line3": 3000, "total_receipts": 10000}
                for month in range(1, 13)
            ],
            "electric_bills": [
                {"period": f"2026-{month:02}", "electricity_sales_tax": 40}
                for month in range(1, 13)
            ],
            "statewide_sales_test": {
                "tax_year": "2025", "all_indiana_establishments_included": True,
                "customer_confirmed": True, "prepared_food_sales": 80000, "total_food_sales": 100000,
            },
            "rate_comparison": {
                "annual_kwh": 60000,
                "current_plan": {"name": "Current", "rate_per_kwh": 0.14, "monthly_fixed_charge": 40, "source_url": "https://utility.example/current"},
                "alternative_plan": {"name": "Alternative", "rate_per_kwh": 0.12, "monthly_fixed_charge": 50, "source_url": "https://utility.example/alternative"},
            },
            })

        self.assertEqual(result["result"], "match")
        self.assertEqual(result["estimate"]["estimated_annual_savings"], 240.0)
        self.assertEqual(result["estimate"]["basis"], "50% of reported electricity sales tax")
        self.assertEqual(result["rate_check"]["estimated_annual_savings"], 1080.0)
        self.assertEqual(result["rate_check"]["result"], "match")
        self.assertEqual(result["rate_check"]["availability"], "uncertain — please check")
        self.assertEqual(result["state_form_draft"]["form"], "ST-200R")
        self.assertEqual(result["state_form_draft"]["fields"]["section_f_prepared_food_receipts"], 96000)
        self.assertEqual(result["state_form_draft"]["fields"]["section_f_prepared_food_line1"], 24000)
        self.assertTrue(result["state_form_draft"]["missing_fields"])
        self.assertFalse(result["state_form_draft"]["signed"])
        self.assertFalse(result["state_form_draft"]["submitted"])
        self.assertIn("customer", result["next_step"].lower())

    def test_below_receipts_threshold_is_no_match_found(self):
        result = calculate_audit({
            "state": "IN", "single_electric_meter": True, "customer_confirmed_receipts": True,
            "sales_months": [
                {"period": f"2026-{month:02}", "prepared_food_receipts": 7000, "total_receipts": 10000}
                for month in range(1, 13)
            ],
            "electric_bills": [
                {"period": f"2026-{month:02}", "electricity_sales_tax": 18}
                for month in range(1, 13)
            ],
            "statewide_sales_test": {
                "tax_year": "2025", "all_indiana_establishments_included": True,
                "customer_confirmed": True, "prepared_food_sales": 70000, "total_food_sales": 100000,
            },
        })

        self.assertEqual(result["result"], f"no match found in Indiana DOR restaurant electricity rule as of {date.today().isoformat()}")
        self.assertIsNone(result["estimate"]["estimated_annual_savings"])
        self.assertIsNone(result["state_form_draft"])

    def test_missing_evidence_or_other_meter_setup_is_uncertain(self):
        missing = calculate_audit({"state": "IN", "sales_months": [], "electric_bills": []})
        multiple_meters = calculate_audit({
            "state": "IN",
            "single_electric_meter": False,
            "customer_confirmed_receipts": True,
            "sales_months": [
                {"period": f"2026-{month:02}", "prepared_food_receipts": 9000, "total_receipts": 10000}
                for month in range(1, 13)
            ],
            "electric_bills": [
                {"period": f"2026-{month:02}", "electricity_sales_tax": 18}
                for month in range(1, 13)
            ],
        })

        self.assertEqual(missing["result"], "uncertain — please check")
        self.assertEqual(multiple_meters["result"], "uncertain — please check")
        self.assertIsNone(missing["estimate"]["estimated_annual_savings"])
        self.assertIsNone(multiple_meters["state_form_draft"])

    def test_rejects_invalid_invoice_tax_and_never_claims_retroactive_refund(self):
        with self.assertRaises(ValueError):
            calculate_audit({
                "state": "IN",
                "single_electric_meter": True,
                "electric_bills": [{"period": "2026-01", "electricity_sales_tax": -1}],
            })
        result = calculate_audit({
            "state": "IN", "single_electric_meter": True, "customer_confirmed_receipts": True,
            "sales_months": [
                {"period": f"2026-{month:02}", "prepared_food_receipts": 9000, "total_receipts": 10000}
                for month in range(1, 13)
            ],
            "electric_bills": [
                {"period": f"2026-{month:02}", "electricity_sales_tax": 18}
                for month in range(1, 13)
            ],
        })
        self.assertNotIn("refund", result["estimate"])
        self.assertEqual(result["estimate"]["estimate_type"], "future annual savings after approval")

    def test_local_location_ratio_cannot_replace_statewide_seller_test(self):
        result = calculate_audit({
            "state": "IN", "single_electric_meter": True, "customer_confirmed_receipts": True,
            "sales_months": [
                {"period": f"2026-{month:02}", "prepared_food_receipts": 9000, "total_receipts": 10000}
                for month in range(1, 13)
            ],
            "electric_bills": [
                {"period": f"2026-{month:02}", "electricity_sales_tax": 18}
                for month in range(1, 13)
            ],
        })

        self.assertEqual(result["result"], "uncertain — please check")
        self.assertIsNone(result["state_form_draft"])
        self.assertIn("all Indiana establishments", result["detail"])

    def test_invalid_or_nonconsecutive_months_are_rejected_or_uncertain(self):
        base = {
            "state": "IN", "single_electric_meter": True, "customer_confirmed_receipts": True,
            "statewide_sales_test": {
                "tax_year": "2025", "all_indiana_establishments_included": True,
                "customer_confirmed": True, "prepared_food_sales": 90000, "total_food_sales": 100000,
            },
            "sales_months": [
                {"period": f"2026-{month:02}", "prepared_food_receipts": 9000, "total_receipts": 10000}
                for month in range(1, 13)
            ],
            "electric_bills": [
                {"period": f"2026-{month:02}", "electricity_sales_tax": 18}
                for month in range(1, 13)
            ],
        }
        malformed = {**base, "electric_bills": [{**base["electric_bills"][0], "period": "2026-99"}, *base["electric_bills"][1:]]}
        with self.assertRaises(ValueError):
            calculate_audit(malformed)
        gap = {**base, "electric_bills": [row for row in base["electric_bills"] if row["period"] != "2026-06"]}

        self.assertEqual(calculate_audit(gap)["result"], "uncertain — please check")

    def test_rate_check_reports_customer_supplied_flat_rate_comparison_without_claiming_availability(self):
        from scripts import utility_audit
        data = json.loads((Path(__file__).parent / "sample_audit.json").read_text(encoding="utf-8"))
        data["rate_comparison"]["alternative_plan"]["rate_per_kwh"] = 0.15
        response = MagicMock()
        response.__enter__.return_value = response
        response.geturl.return_value = "https://utility.example/rates"
        response.read.return_value = b"rate schedule"

        with patch.object(utility_audit.urllib.request, "urlopen", return_value=response):
            rate_check = calculate_audit(data)["rate_check"]

        self.assertEqual(rate_check["result"], f"no match found in customer-provided Indiana published flat-rate options as of {date.today().isoformat()}")
        self.assertEqual(rate_check["estimated_annual_savings"], -720.0)
        self.assertEqual(rate_check["availability"], "uncertain — please check")
        self.assertEqual(rate_check["source_status"], "reachable_unverified")
        self.assertIn("official source identity", rate_check["detail"])

    def test_rate_check_verifies_source_reachability_and_rejects_unavailable_or_nonofficial_url(self):
        from scripts import utility_audit
        data = json.loads((Path(__file__).parent / "sample_audit.json").read_text(encoding="utf-8"))
        response = MagicMock()
        response.__enter__.return_value = response
        response.geturl.return_value = "https://utility.example/rates"
        response.read.return_value = b"rate schedule"
        with patch.object(utility_audit.urllib.request, "urlopen", return_value=response) as urlopen:
            check = calculate_audit(data)["rate_check"]
        self.assertEqual(check["source_status"], "reachable_unverified")
        self.assertEqual(urlopen.call_count, 2)
        self.assertIn("not independently confirmed", check["detail"])

        data["rate_comparison"]["alternative_plan"]["source_url"] = "http://utility.example/rates"
        with patch.object(utility_audit.urllib.request, "urlopen", return_value=response):
            check = calculate_audit(data)["rate_check"]
        self.assertEqual(check["source_status"], "invalid")
        self.assertEqual(check["result"], "uncertain — please check")

        data["rate_comparison"]["alternative_plan"]["source_url"] = "https://127.0.0.1/admin"
        with patch.object(utility_audit.urllib.request, "urlopen", return_value=response) as urlopen:
            check = calculate_audit(data)["rate_check"]
        self.assertEqual(check["source_status"], "invalid")
        urlopen.assert_called_once()

        data["rate_comparison"]["alternative_plan"]["source_url"] = "https://["
        with patch.object(utility_audit.urllib.request, "urlopen") as urlopen:
            check = calculate_audit(data)["rate_check"]
        self.assertEqual(check["source_status"], "invalid")
        urlopen.assert_called_once()

        with patch.object(utility_audit.urllib.request, "urlopen", side_effect=OSError("not found")):
            check = calculate_audit(json.loads((Path(__file__).parent / "sample_audit.json").read_text(encoding="utf-8")))["rate_check"]
        self.assertEqual(check["source_status"], "unavailable")
        self.assertEqual(check["result"], "uncertain — please check")

    def test_manifest_has_exact_dor_rules_and_st200r_links_and_billing_stays_disabled(self):
        manifest = json.loads((Path(__file__).parents[1] / "venture.json").read_text(encoding="utf-8"))
        owner_text = " ".join(step["detail"] for step in manifest["your_steps"])
        links = [link for step in manifest["your_steps"] for link in step["links"]]
        self.assertIn("https://forms.in.gov/Download.aspx?id=16301", links)
        self.assertIn("https://www.in.gov/dor/files/sib11.pdf", links)
        self.assertIn("https://www.in.gov/dor/files/sib29.pdf", links)
        self.assertIn("sign as the customer", owner_text.lower())
        self.assertIn("submit it to indiana dor", owner_text.lower())
        self.assertIn("disabled", manifest["product"]["billing"].lower())
        self.assertIn("legal basis", manifest["product"]["billing"].lower())


if __name__ == "__main__":
    unittest.main()
