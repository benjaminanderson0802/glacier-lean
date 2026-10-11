from pathlib import Path
import re

from workflow import check_route_card, completed_jobber_jobs, render_postcard_pdf


def test_postcard_print_proof_is_two_eddm_flat_pages(tmp_path: Path):
    output = tmp_path / "proof.pdf"
    render_postcard_pdf(
        {"dealer_name": "Sample Heating", "town": "Exampleville", "sender": "Sample Heating"},
        output,
    )

    pdf = output.read_bytes()
    assert pdf.startswith(b"%PDF-")
    assert len(re.findall(rb"/Type /Page\b", pdf)) == 2
    assert pdf.count(b"/MediaBox [0 0 828 450]") == 2  # 11.5 x 6.25 inches at 72 points/inch
    assert b"11.5 x 6.25 inch USPS EDDM Retail flat proof" in pdf
    assert b"Sample Heating" in pdf
    assert b"Exampleville" in pdf


def test_jobber_intake_requests_completed_job_metadata_only():
    class ReadOnlyJobber:
        def test_connection(self):
            return {"account": "Test dealer"}

        def graphql(self, query, variables):
            assert "client" not in query
            assert "property" not in query
            assert "customFields" not in query
            assert variables == {"first": 50, "after": None}
            return {"jobs": {
                "nodes": [
                    {"id": "job-1", "jobStatus": "COMPLETED", "title": "Install"},
                    {"id": "job-2", "jobStatus": "ACTIVE", "title": "Estimate"},
                ],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }}

    assert completed_jobber_jobs(ReadOnlyJobber()) == (
        "Test dealer",
        [{"id": "job-1", "jobStatus": "COMPLETED", "title": "Install"}],
    )


def test_eddm_flat_enforces_specific_five_inch_minimum():
    from json import loads
    from pathlib import Path

    fixture = loads((Path(__file__).parents[1] / "fixtures/eddm_route_card.json").read_text())
    fixture["mailpiece"].update(length_inches=4.99, height_inches=3.5, thickness_inches=0.26)
    rejected = check_route_card(fixture)
    assert rejected["verdict"] == "fail"
    assert "5–15 inches long" in " ".join(rejected["issues"])

    fixture["mailpiece"]["length_inches"] = 5
    accepted = check_route_card(fixture)
    assert accepted["verdict"] == "pass"
