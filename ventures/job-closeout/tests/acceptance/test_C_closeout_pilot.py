"""Independent frozen cases for the five-packet closeout pilot.

Synthetic API fields follow ACCEPTANCE.md. Equipment, work summary, and invoice
reference are local mappings carried in Jobber customFields, not official API
fields. This suite exercises the existing generator without changing it.
"""
from __future__ import annotations

import importlib.util
import hashlib
import json
import socket
import sys
from pathlib import Path

import pytest


KIT = Path(__file__).resolve().parents[2]
ROOT = KIT.parents[1]
sys.path.insert(0, str(ROOT))
GENERATOR_PATH = KIT / "scripts/generate_packet.py"
UNCERTAIN = "uncertain — please check"
_ORIGINAL_CONNECT = socket.socket.connect
_ORIGINAL_CONNECT_EX = socket.socket.connect_ex


def load_generator():
    spec = importlib.util.spec_from_file_location("C_closeout_pilot_generator", GENERATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _block_network(sock, address):
    raise AssertionError(f"fixture-only pilot check attempted network connection to {address!r}")


@pytest.fixture(autouse=True)
def fixture_runs_are_offline(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", _block_network)
    monkeypatch.setattr(socket.socket, "connect_ex", _block_network)


def custom_fields(index: int) -> list[dict[str, str]]:
    """Local packet mappings encoded as documented Jobber custom text fields."""
    return [
        {"__typename": "CustomFieldText", "label": "Work Summary", "valueText": f"Synthetic work summary {index}"},
        {"__typename": "CustomFieldText", "label": "Equipment Brand", "valueText": f"Brand {index}"},
        {"__typename": "CustomFieldText", "label": "Equipment Model", "valueText": f"Model {index}"},
        {"__typename": "CustomFieldText", "label": "Equipment Serial", "valueText": f"SERIAL-{index:04d}"},
        {"__typename": "CustomFieldText", "label": "Invoice Reference", "valueText": f"INV-{index:04d}"},
    ]


def completed_job(index: int) -> dict:
    return {
        "id": f"Z2lkOi8vSm9iYmVyL0pvYi9zeW50aGV0aWMt{index}",
        "jobNumber": 9100 + index,
        "title": f"Synthetic completed job {index}",
        "jobStatus": "COMPLETED",
        "completedAt": f"2026-10-{index + 1:02d}T15:30:00-05:00",
        "customFields": custom_fields(index),
        "client": {"name": f"Synthetic customer {index}"},
        "property": {"address": {"city": f"Test City {index}", "province": "TX", "postalCode": f"78{index:03d}"}},
    }


def envelope(jobs: list[dict], *, page_info: dict | None = None) -> dict:
    return {
        "data": {
            "account": {"name": "Synthetic Closeout Shop"},
            "jobs": {
                "nodes": jobs,
                "pageInfo": page_info or {"hasNextPage": False, "endCursor": None},
            },
        },
        "extensions": {"versioning": {"version": "2026-04-16"}},
    }


def write_source(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def test_five_synthetic_packets_retain_source_and_remain_reviewable(tmp_path, monkeypatch, capsys):
    generator = load_generator()

    def unexpected_client(*args, **kwargs):
        raise AssertionError("fixture mode must not instantiate the live Jobber connector")

    monkeypatch.setattr(generator, "JobberClient", unexpected_client)
    jobs = [completed_job(index) for index in range(1, 6)]
    source = write_source(tmp_path / "five-synthetic-jobs.json", envelope(jobs))
    output = tmp_path / "packets"

    assert generator.main(["--fixture", str(source), "--output-dir", str(output)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["packets_created"] == 5
    assert report["external_actions"] == "none"
    assert len(list(output.glob("*.md"))) == len(list(output.glob("*.pdf"))) == 5
    assert {path.suffix for path in output.iterdir()} == {".md", ".pdf"}

    for index in range(1, 6):
        stem = hashlib.sha256(jobs[index - 1]["id"].encode()).hexdigest()[:24]
        markdown = (output / f"job-{stem}.md").read_text(encoding="utf-8")
        pdf = (output / f"job-{stem}.pdf").read_bytes()
        for supplied_value in (
            f"Synthetic completed job {index}",
            f"Synthetic customer {index}",
            f"Synthetic work summary {index}",
            f"Brand {index}",
            f"Model {index}",
            f"SERIAL-{index:04d}",
            f"INV-{index:04d}",
            f"Test City {index}, TX, 78{index:03d}",
        ):
            assert supplied_value in markdown
            assert supplied_value.encode("utf-8") in pdf
        assert f"2026-10-{index + 1:02d}" in markdown
        assert b"not a code, safety, or workmanship certification" in pdf
        assert b"compliance" not in pdf.lower()
        assert b"Photo 1: add approved completion photo" in pdf
        assert b"Warranty/registration: confirm the manufacturer's current terms" in pdf


def test_missing_source_values_are_uncertain_and_not_invented(tmp_path, capsys):
    generator = load_generator()
    missing = {
        "id": "Z2lkOi8vSm9iYmVyL0pvYi9taXNzaW5n",
        "jobStatus": "COMPLETED",
        "completedAt": None,
        "customFields": [],
        "client": None,
        "property": None,
    }
    source = write_source(tmp_path / "missing-fields.json", envelope([missing]))
    output = tmp_path / "missing-packet"

    assert generator.main(["--fixture", str(source), "--output-dir", str(output)]) == 0
    report = json.loads(capsys.readouterr().out)
    markdown = next(output.glob("*.md")).read_text(encoding="utf-8")
    assert report["packets_created"] == 1
    assert markdown.count(UNCERTAIN) >= 5
    assert "None" not in markdown
    assert "null" not in markdown.casefold()
    assert "## Equipment\n- uncertain — please check; add or confirm equipment details." in markdown
    assert "not a code, safety, or workmanship certification" in markdown


def test_malformed_completion_date_is_uncertain_not_a_date_fact(tmp_path, capsys):
    generator = load_generator()
    job = completed_job(1)
    job["completedAt"] = "not-a-date"
    source = write_source(tmp_path / "malformed-date.json", envelope([job]))
    output = tmp_path / "malformed-date-packet"

    assert generator.main(["--fixture", str(source), "--output-dir", str(output)]) == 0
    capsys.readouterr()
    markdown = next(output.glob("*.md")).read_text(encoding="utf-8")
    assert f"**Completed:** {UNCERTAIN}" in markdown
    assert "not-a-date" not in markdown


@pytest.mark.parametrize(
    "case",
    ["partial_page", "partial_graphql", "source_outage", "rate_limited"],
)
def test_incomplete_or_unavailable_source_creates_no_packet(tmp_path, capsys, case):
    generator = load_generator()
    payload = envelope([completed_job(1)])
    if case == "partial_page":
        payload["data"]["jobs"]["pageInfo"] = {"hasNextPage": True, "endCursor": "next-page"}
    elif case == "partial_graphql":
        payload["errors"] = [{"message": "Field resolution failed"}]
    else:
        payload["errors"] = [{"message": "Service unavailable" if case == "source_outage" else "Throttled"}]
        payload["data"] = None
    source = write_source(tmp_path / f"{case}.json", payload)
    output = tmp_path / f"{case}-packets"

    assert generator.main(["--fixture", str(source), "--output-dir", str(output)]) != 0
    error = json.loads(capsys.readouterr().err)
    assert error["status"] == "uncertain"
    assert "uncertain" in error["result"]
    assert error["external_actions"] == "none"
    assert not list(output.glob("*.md")) if output.exists() else True
    assert not list(output.glob("*.pdf")) if output.exists() else True
