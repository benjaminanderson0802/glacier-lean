from ventures.blocks.rules import check


def test_cpsc_good_certificate_passes_with_citations():
    fields = {
        "product_id": "ABC-7",
        "citation_codes": ["16 CFR part 1303"],
        "manufacture_date": "2026-05",
        "manufacture_place": {"name": "Example Works", "address": "1 Main St", "contact": "ops@example.test"},
        "product_test_date": "2026-06-01",
        "testing_laboratory": {"name": "Example Lab", "address": "2 Main St", "contact": "lab@example.test"},
        "point_of_contact": {"name": "Record Keeper", "address": "3 Main St", "contact": "records@example.test"},
    }

    result = check(fields, "cpsc_efiling.json")

    assert result["verdict"] == "pass"
    assert result["results"]
    assert all(item["cite"] for item in result["results"])
    assert all(item["verdict"] == "pass" for item in result["results"])


def test_cpsc_hand_made_bad_certificate_fails_with_citations():
    fields = {
        "product_id": "",
        "citation_codes": [],
        "manufacture_date": "not-a-date",
        "manufacture_place": {"name": "", "address": "", "contact": ""},
        "product_test_date": "",
        "testing_laboratory": {"name": "", "address": "", "contact": ""},
        "point_of_contact": {"name": "", "address": "", "contact": ""},
    }

    result = check(fields, "cpsc_efiling.json")

    assert result["verdict"] == "fail"
    assert any(item["verdict"] == "fail" for item in result["results"])
    assert all(item["cite"] for item in result["results"])


def test_fda_good_cosmetics_listing_passes_and_missing_data_is_uncertain():
    fields = {
        "responsible_person_name": "Example Beauty LLC",
        "responsible_person_phone": "+1-555-0101",
        "product_category_codes": ["06A2"],
        "product_name": "Daily Conditioner",
        "fragrance_or_flavor": ["fragrance"],
        "facility_fei": ["1234567890"],
        "ingredients": ["water", "glycerin"],
        "ingredient_products": {"water": ["Daily Conditioner"], "glycerin": ["Daily Conditioner"]},
    }

    good = check(fields, "fda_mocra_listing.json")
    incomplete = check({"product_name": "Daily Conditioner"}, "fda_mocra_listing.json")

    assert good["verdict"] == "pass"
    assert all(item["cite"] for item in good["results"])
    assert incomplete["verdict"] == "uncertain"
    assert all(item["cite"] for item in incomplete["results"])

