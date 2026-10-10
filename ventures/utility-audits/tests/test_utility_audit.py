import unittest
import json
from datetime import date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.utility_audit import calculate_audit


class UtilityAuditAcceptanceTests(unittest.TestCase):
    def test_eligible_indiana_restaurant_gets_half_electricity_tax_estimate_and_unsigned_draft(self):
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
        data = json.loads((Path(__file__).parent / "sample_audit.json").read_text(encoding="utf-8"))
        data["rate_comparison"]["alternative_plan"]["rate_per_kwh"] = 0.15

        rate_check = calculate_audit(data)["rate_check"]

        self.assertEqual(rate_check["result"], f"no match found in customer-provided Indiana published flat-rate options as of {date.today().isoformat()}")
        self.assertEqual(rate_check["estimated_annual_savings"], -720.0)
        self.assertEqual(rate_check["availability"], "uncertain — please check")
        self.assertIn("not fetched or validated", rate_check["detail"])


if __name__ == "__main__":
    unittest.main()
