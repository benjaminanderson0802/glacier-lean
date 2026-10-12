"""Prepare local Markdown and PDF closeout packets from completed Jobber jobs."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import textwrap
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from ventures.blocks.connectors import JobberClient

UNCERTAIN = "uncertain — please check"
PHOTO_PLACEHOLDERS = [
    "Photo 1: add approved completion photo",
    "Photo 2: add approved equipment-label photo",
]


def _fields(job: dict[str, Any]) -> dict[str, str]:
    values: dict[str, str] = {}
    for field in job.get("customFields") or []:
        if field.get("__typename") == "CustomFieldText" and field.get("label"):
            value = str(field.get("valueText") or "").strip()
            if value:
                values[str(field["label"]).strip().casefold()] = value
    return values


def build_packet(job: dict[str, Any], business_name: str) -> dict[str, Any]:
    if str(job.get("jobStatus") or "").casefold() not in {"completed", "complete"}:
        raise ValueError("Only completed Jobber jobs can become closeout packets.")
    client = job.get("client") or {}
    address = (job.get("property") or {}).get("address") or {}
    fields = _fields(job)
    equipment = []
    brand = fields.get("equipment brand", "")
    model = fields.get("equipment model", "")
    serial = fields.get("equipment serial", "")
    if brand or model or serial:
        equipment.append({"brand": brand or UNCERTAIN, "model": model or UNCERTAIN, "serial": serial or UNCERTAIN})
    completed_at = str(job.get("completedAt") or "").strip()
    completion_date = UNCERTAIN
    if completed_at and "T" in completed_at.upper():
        try:
            parsed_completion = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
        except ValueError:
            pass
        else:
            completion_date = parsed_completion.date().isoformat()
    return {
        "business_name": business_name,
        "job_id": str(job.get("id") or ""),
        "completion_status": "completed",
        "job_number": str(job.get("jobNumber") or UNCERTAIN),
        "job_title": str(job.get("title") or UNCERTAIN),
        "completion_date": completion_date,
        "customer_name": str(client.get("name") or UNCERTAIN),
        "service_location": ", ".join(str(address.get(key) or "").strip() for key in ("city", "province", "postalCode") if address.get(key)) or UNCERTAIN,
        "work_summary": fields.get("work summary", str(job.get("title") or UNCERTAIN)),
        "equipment": equipment,
        "warranty_reminder": "Warranty/registration: confirm the manufacturer's current terms and register the equipment if required. This packet does not determine coverage or a deadline.",
        "photos": PHOTO_PLACEHOLDERS.copy(),
        "invoice_reference": fields.get("invoice reference", UNCERTAIN),
        "review_note": "This packet records supplied job details; it is not a code, safety, or workmanship certification.",
    }


def render_markdown(packet: dict[str, Any]) -> str:
    equipment_lines = [
        f"- {item['brand']} {item['model']} (serial: {item['serial']})" for item in packet["equipment"]
    ] or [f"- {UNCERTAIN}; add or confirm equipment details."]
    return "\n".join([
        f"# Job closeout: {packet['job_title']}",
        "",
        f"**Prepared by:** {packet['business_name']}",
        f"**Job:** {packet['job_number']}  ",
        f"**Completed:** {packet['completion_date']}  ",
        f"**Customer:** {packet['customer_name']}  ",
        f"**Service location:** {packet['service_location']}",
        "",
        "## Work summary",
        packet["work_summary"],
        "",
        "## Equipment",
        *equipment_lines,
        "",
        "## Warranty / registration reminder",
        packet["warranty_reminder"],
        "",
        "## Photos to attach",
        *(f"- {photo}" for photo in packet["photos"]),
        "",
        "## Invoice reference",
        packet["invoice_reference"],
        "",
        f"> {packet['review_note']}",
        "",
    ])


def _pdf_escape(value: str) -> bytes:
    """Encode Unicode for the built-in Adobe GB1 composite font without transliteration."""
    return value.encode("utf-16-be").hex().upper().encode("ascii")


def _pdf_show_text(line: str) -> bytes:
    """Use WinAnsi for Western glyphs and the standard GB1 font for other scripts."""
    runs: list[tuple[str, str]] = []
    current_font = "F1"
    current_text = ""
    for char in unicodedata.normalize("NFC", line):
        try:
            char.encode("cp1252")
            font = "F1"
        except UnicodeEncodeError:
            font = "F2"
        if font != current_font and current_text:
            runs.append((current_font, current_text))
            current_text = ""
        current_font = font
        current_text += char
    if current_text:
        runs.append((current_font, current_text))
    commands = bytearray()
    for font, text in runs:
        encoded = text.encode("cp1252").hex().upper().encode("ascii") if font == "F1" else _pdf_escape(text)
        commands.extend(b"/" + font.encode("ascii") + b" 10 Tf <" + encoded + b"> Tj\n")
    return bytes(commands)


def render_pdf(markdown: str) -> bytes:
    """Write a text PDF with a built-in composite font and lossless UTF-8 source text."""
    lines: list[str] = []
    for raw in markdown.splitlines():
        line = raw.replace("**", "").replace("## ", "").replace("# ", "").replace("> ", "")
        if line.startswith("- "):
            line = "  " + line
        lines.extend(textwrap.wrap(line, width=92, replace_whitespace=False, drop_whitespace=True) or [""])
    pages = [lines[offset:offset + 48] for offset in range(0, len(lines), 48)] or [[]]
    objects: list[bytes] = []
    page_ids = [6 + index * 2 for index in range(len(pages))]
    content_ids = [page_id + 1 for page_id in page_ids]
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode("ascii"))
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    objects.append(
        b"<< /Type /Font /Subtype /Type0 /BaseFont /STSong-Light /Encoding /UniGB-UCS2-H /DescendantFonts [5 0 R] >>"
    )
    objects.append(
        b"<< /Type /Font /Subtype /CIDFontType0 /BaseFont /STSong-Light "
        b"/CIDSystemInfo << /Registry (Adobe) /Ordering (GB1) /Supplement 5 >> /DW 1000 >>"
    )
    for page_id, content_id, page_lines in zip(page_ids, content_ids, pages):
        stream = bytearray(b"BT\n50 760 Td\n14 TL\n")
        for line in page_lines:
            stream.extend(_pdf_show_text(line))
            stream.extend(b"T*\n")
        stream.extend(b"ET\n")
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {content_id} 0 R >>".encode("ascii")
        )
        objects.append(b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + bytes(stream) + b"endstream")
    # Keep a byte-exact UTF-8 text copy in legal PDF comments for readers that do
    # not support the built-in CJK font resources. Rendered page text remains
    # Unicode text encoded for the composite font above.
    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n%source-utf8 ")
    for source_line in markdown.splitlines():
        # Each source line is a PDF comment: neutralize carriage returns and
        # other line terminators so job text cannot inject PDF operators.
        pdf.extend(source_line.replace("\r", "\\r").encode("utf-8"))
        pdf.extend(b"\n%source-utf8 ")
    pdf.extend(b"\n")
    offsets = [0]
    for object_id, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{object_id} 0 obj\n".encode("ascii") + body + b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii"))
    return bytes(pdf)


def write_packet(packet: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_root = output_dir.resolve(strict=True)
    identity = str(packet.get("job_id") or "").strip()
    if not identity:
        raise ValueError("A source job ID is required before writing a packet.")
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
    stem = f"job-{digest}"
    md_path = output_dir / f"{stem}.md"
    pdf_path = output_dir / f"{stem}.pdf"
    if md_path.parent.resolve(strict=True) != output_root or pdf_path.parent.resolve(strict=True) != output_root:
        raise ValueError("Packet paths must stay inside the selected output directory.")
    markdown = render_markdown(packet)
    pdf = render_pdf(markdown)
    markdown_created = False
    pdf_created = False
    try:
        with md_path.open("x", encoding="utf-8") as stream:
            markdown_created = True
            stream.write(markdown)
        with pdf_path.open("xb") as stream:
            pdf_created = True
            stream.write(pdf)
    except FileExistsError as exc:
        if markdown_created:
            md_path.unlink(missing_ok=True)
        if pdf_created:
            pdf_path.unlink(missing_ok=True)
        raise ValueError("A packet for this source job already exists; no files were overwritten.") from exc
    except OSError:
        if markdown_created:
            md_path.unlink(missing_ok=True)
        if pdf_created:
            pdf_path.unlink(missing_ok=True)
        raise
    return md_path, pdf_path


def _load_fixture(path: Path) -> tuple[str, list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Jobber response is not an object; result is uncertain.")
    if payload.get("errors"):
        raise ValueError(f"Jobber returned GraphQL errors; {UNCERTAIN}; no packet was created.")
    if payload.get("extensions", {}).get("versioning", {}).get("version") != "2026-04-16":
        raise ValueError("Fixture must match the Jobber API version used by the read-only connector.")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise ValueError(f"Jobber returned no complete data; {UNCERTAIN}; no packet was created.")
    account = data.get("account")
    jobs_connection = data.get("jobs")
    if not isinstance(account, dict) or not isinstance(jobs_connection, dict):
        raise ValueError(f"Jobber response is missing account or jobs data; {UNCERTAIN}.")
    page_info = jobs_connection.get("pageInfo")
    nodes = jobs_connection.get("nodes")
    if not isinstance(nodes, list) or not isinstance(page_info, dict):
        raise ValueError(f"Jobber response is missing job rows or page status; {UNCERTAIN}.")
    if page_info.get("hasNextPage") is not False:
        raise ValueError(f"Jobber response has more pages or an unknown page status; {UNCERTAIN}.")
    if not all(isinstance(job, dict) for job in nodes):
        raise ValueError(f"Jobber response contains malformed job data; {UNCERTAIN}.")
    business = account.get("name")
    if not isinstance(business, str) or not business.strip():
        raise ValueError(f"Jobber account name is missing; {UNCERTAIN}.")
    return business, nodes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--fixture", type=Path, help="use a local Jobber-shaped fixture; stays offline")
    source.add_argument("--jobber", action="store_true", help="read jobs via the existing read-only Jobber client")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    client = None
    try:
        if args.fixture:
            business, jobs = _load_fixture(args.fixture)
            intake = "fixture"
        else:
            client = JobberClient()
            account = client.test_connection()
            business = str(account.get("account") or "Jobber business")
            jobs = client.get_jobs(max_pages=5)
            intake = "Jobber read-only connector"
        packets = []
        for job in jobs:
            if str(job.get("jobStatus") or "").casefold() not in {"completed", "complete"}:
                continue
            packet = build_packet(job, business)
            markdown, pdf = write_packet(packet, args.output_dir)
            packets.append({"job_number": packet["job_number"], "markdown": str(markdown), "pdf": str(pdf)})
        print(json.dumps({"source": intake, "packets_created": len(packets), "packets": packets, "external_actions": "none"}, indent=2))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError, RuntimeError) as exc:
        print(json.dumps({"status": "uncertain", "result": UNCERTAIN, "error": str(exc), "external_actions": "none"}, ensure_ascii=False), file=sys.stderr)
        return 2
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
