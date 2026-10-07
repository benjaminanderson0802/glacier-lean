"""Offline OCR for image uploads, isolated in a capped child process."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

_TIMEOUT_SECONDS = 60
_MAX_TEXT_BYTES = 2 * 1024 * 1024

_SCRIPT = r'''
import json, os, shutil, subprocess, sys, tempfile, warnings
try:
    import resource
    cap = 2 * 1024 * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
except (ImportError, OSError, ValueError):
    pass
try:
    from PIL import Image, ImageOps
    warnings.simplefilter('error', Image.DecompressionBombWarning)
    source = sys.argv[1]
    fd, prepared = tempfile.mkstemp(suffix='.png')
    os.close(fd)
    try:
        with Image.open(source) as image:
            image.seek(0)
            image = ImageOps.exif_transpose(image)
            image.thumbnail((4000, 4000), Image.Resampling.LANCZOS)
            image.convert('RGB').save(prepared, format='PNG')
        binary = shutil.which('tesseract')
        if not binary:
            raise FileNotFoundError('tesseract')
        langs = os.environ.get('GLACIER_OCR_LANGS', 'eng').strip() or 'eng'
        result = subprocess.run([binary, prepared, 'stdout', '-l', langs], capture_output=True, timeout=55, check=False)
        if result.returncode:
            raise RuntimeError('ocr_failed')
        print(json.dumps({'text': result.stdout[:2097152].decode('utf-8', 'replace')}))
    finally:
        try: os.unlink(prepared)
        except OSError: pass
except Exception as exc:
    bomb = False
    try:
        from PIL import Image as _PIL
        bomb = isinstance(exc, _PIL.DecompressionBombError) or isinstance(exc, _PIL.DecompressionBombWarning)
    except (AttributeError, ImportError):
        pass
    print(json.dumps({'error': 'decompression_bomb' if bomb else 'ocr_failed'}))
'''


def recognize(path: Path) -> tuple[str, str | None]:
    """Return recognized text and a plain internal reason when OCR cannot run."""
    try:
        result = subprocess.run(
            [sys.executable, "-c", _SCRIPT, str(path)],
            capture_output=True,
            timeout=_TIMEOUT_SECONDS,
            check=False,
            env=dict(os.environ, MALLOC_ARENA_MAX="2"),
        )
    except subprocess.TimeoutExpired:
        return "", "timeout"
    if result.returncode:
        return "", "ocr_failed"
    try:
        payload = json.loads(result.stdout.decode("utf-8", errors="replace"))
    except (ValueError, TypeError):
        return "", "ocr_failed"
    return str(payload.get("text", ""))[:_MAX_TEXT_BYTES], payload.get("error")
