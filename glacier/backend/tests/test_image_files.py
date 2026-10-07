"""Acceptance tests for offline, bounded OCR on uploaded images."""

import os
import struct
import zlib

import httpx
import pytest


def _fake_tesseract(tmp_path, body, *, sleep=0):
    exe = tmp_path / "tesseract"
    marker = tmp_path / "tesseract-called"
    exe.write_text(f"#!/bin/sh\ntouch '{marker}'\nsleep {sleep}\nprintf '%s\\n' '{body}'\n", encoding="utf-8")
    exe.chmod(0o755)
    return exe


def _png(width=12, height=8):
    def chunk(kind, payload):
        value = kind + payload
        return struct.pack(">I", len(payload)) + value + struct.pack(">I", zlib.crc32(value) & 0xffffffff)
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    pixels = zlib.compress((b"\x00" + b"\xff\xff\xff" * width) * height)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", pixels) + chunk(b"IEND", b"")


def test_image_upload_ocr_note_is_searchable(monkeypatch, make_server, tmp_path):
    _fake_tesseract(tmp_path, "Nebula receipt searchable phrase")
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}")
    server = make_server().start()
    response = httpx.post(server.url + "/api/files", files={"file": ("receipt.png", _png(), "image/png")})
    assert response.status_code == 200, response.text
    assert (tmp_path / "tesseract-called").exists()
    item = response.json()
    assert item["note"] == "files/Inbox/receipt.png.md"
    note = os.path.join(server.home, "vault", item["note"])
    assert "Text found in the image" in open(note, encoding="utf-8").read()
    found = httpx.get(server.url + "/api/memory/search", params={"q": "Nebula"}).json()
    assert any(row["path"] == item["note"] for row in found)


def test_image_without_tesseract_is_stored_with_install_hint(monkeypatch, make_server, tmp_path):
    path = os.pathsep.join(item for item in os.environ.get("PATH", "").split(os.pathsep)
                           if item and not os.path.exists(os.path.join(item, "tesseract")))
    monkeypatch.setenv("PATH", path)
    server = make_server().start()
    response = httpx.post(server.url + "/api/files", files={"file": ("photo.png", _png(), "image/png")})
    assert response.status_code == 200, response.text
    item = response.json()
    assert os.path.isfile(os.path.join(server.home, item["path"]))
    note = open(os.path.join(server.home, "vault", item["note"]), encoding="utf-8").read()
    assert "Tesseract" in note and "https://github.com/tesseract-ocr/tesseract" in note
    assert "searchable" in note.lower()


def test_huge_dimension_image_is_refused_cleanly(server):
    # Valid PNG header with dimensions beyond Pillow's decompression-bomb limit.
    huge = bytearray(_png())
    huge[16:24] = struct.pack(">II", 100_000, 100_000)
    huge[29:33] = struct.pack(">I", zlib.crc32(bytes(huge[12:29])) & 0xffffffff)
    response = httpx.post(server.url + "/api/files", files={"file": ("huge.png", bytes(huge), "image/png")})
    assert response.status_code == 200, response.text
    assert "image" in response.json().get("message", "").lower()


def test_ocr_timeout_is_enforced(monkeypatch, tmp_path):
    _fake_tesseract(tmp_path, "too late", sleep=2)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}")
    image = tmp_path / "slow.png"
    image.write_bytes(_png())
    import ocr
    monkeypatch.setattr(ocr, "_TIMEOUT_SECONDS", 0.2)
    text, error = ocr.recognize(image)
    assert text == ""
    assert error == "timeout"
    assert (tmp_path / "tesseract-called").exists()


@pytest.mark.parametrize("binary,version,found", [(True, "tesseract 5.4.1", True), (False, "", False)])
def test_system_check_reports_tesseract(binary, version, found, monkeypatch, tmp_path):
    import system_check

    system_check.clear_cache()
    script = tmp_path / "tesseract"
    script.write_text(f"#!/bin/sh\nprintf '{version}\\n'\n", encoding="utf-8")
    script.chmod(0o755)
    monkeypatch.setattr(system_check.shutil, "which", lambda name: str(script) if binary and name == "tesseract" else None)
    monkeypatch.setattr(system_check, "_run", lambda command, **kwargs: version if command[0] == str(script) else "")
    result = system_check.check_system()
    assert result["tools"]["tesseract"] == {"found": found, "version": version}
