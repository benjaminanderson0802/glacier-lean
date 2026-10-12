from __future__ import annotations

import importlib.util
import ipaddress
import json
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VENTURE = ROOT / "ventures/job-closeout"
FIXTURE = VENTURE / "tests/fixtures/jobber_completed_job.json"
_ORIGINAL_CONNECT = socket.socket.connect


def _blocked_connect(sock, address):
    if isinstance(address, tuple) and address:
        try:
            loopback = ipaddress.ip_address(address[0]).is_loopback
        except ValueError:
            loopback = False
        frame = sys._getframe(1)
        socketpair = asyncio = False
        while frame is not None:
            filename = frame.f_code.co_filename.replace("\\", "/")
            socketpair |= frame.f_code.co_name == "socketpair" and filename.endswith("/socket.py")
            asyncio |= "/asyncio/" in filename
            frame = frame.f_back
        if loopback and socketpair and asyncio:
            return _ORIGINAL_CONNECT(sock, address)
    raise AssertionError(f"fixture generation attempted network connection to {address!r}")


def _load_generator():
    path = VENTURE / "scripts/generate_packet.py"
    spec = importlib.util.spec_from_file_location("job_closeout_generator", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fixture_builds_one_customer_packet_markdown_pdf_without_egress(tmp_path, monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", _blocked_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", _blocked_connect)
    generator = _load_generator()
    output = tmp_path / "packet"
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    jobs = payload["data"]["jobs"]["nodes"]
    job = next(item for item in jobs if item["jobStatus"] == "COMPLETED")

    record = generator.build_packet(job, "Fixture Comfort Systems")
    md_path, pdf_path = generator.write_packet(record, output)
    markdown = md_path.read_text(encoding="utf-8")
    pdf = pdf_path.read_bytes()

    assert record["job_number"] == "9001"
    assert record["completion_status"] == "completed"
    assert record["invoice_reference"] == "INV-9001"
    assert record["equipment"] == [{"brand": "Carrier", "model": "Infinity 24", "serial": "ABC123456789"}]
    assert record["photos"] == ["Photo 1: add approved completion photo", "Photo 2: add approved equipment-label photo"]
    assert "Warranty/registration: confirm the manufacturer's current terms and register the equipment if required." in markdown
    assert "This packet records supplied job details; it is not a code, safety, or workmanship certification." in markdown
    assert "Maya Rivera" in markdown
    assert pdf.startswith(b"%PDF-")
    assert b"INV-9001" in pdf
    assert pdf_path.stat().st_size > 500


def test_uncompleted_or_missing_job_fields_are_not_presented_as_facts():
    generator = _load_generator()
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    jobs = fixture["data"]["jobs"]["nodes"]
    try:
        generator.build_packet(jobs[1], "Fixture Comfort Systems")
    except ValueError as exc:
        assert "completed" in str(exc).casefold()
    else:
        raise AssertionError("an upcoming job must not become a closeout packet")

    completed = dict(jobs[0], customFields=[])
    packet = generator.build_packet(completed, "Fixture Comfort Systems")
    assert packet["work_summary"] == "Heat pump installation"
    assert packet["equipment"] == []
    assert packet["invoice_reference"] == "uncertain — please check"
    assert "uncertain — please check" in generator.render_markdown(packet)


def test_jobber_client_mode_is_read_only_and_filters_completed_jobs(monkeypatch, tmp_path):
    generator = _load_generator()
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    calls = []

    class FakeJobberClient:
        def test_connection(self):
            calls.append("connection")
            return {"connected": True, "account": "Fixture Comfort Systems"}

        def get_jobs(self, **kwargs):
            calls.append(("get_jobs", kwargs))
            return fixture["data"]["jobs"]["nodes"]

        def close(self):
            calls.append("closed")

    monkeypatch.setattr(generator, "JobberClient", FakeJobberClient)
    assert generator.main(["--jobber", "--output-dir", str(tmp_path)]) == 0
    assert calls == ["connection", ("get_jobs", {"max_pages": 5}), "closed"]
    assert len(list(tmp_path.glob("*.md"))) == len(list(tmp_path.glob("*.pdf"))) == 1
