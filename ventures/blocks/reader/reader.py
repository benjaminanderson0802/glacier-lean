from __future__ import annotations

import csv
import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


_MODEL_DEFAULT = "granite3.3:2b"
_OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
_MODEL_TIMEOUT = float(os.environ.get("GLACIER_READER_MODEL_TIMEOUT", "60"))


def _schema_names(schema: Any, pages: list[tuple[int, str]]) -> dict[str, list[str]]:
    if isinstance(schema, dict):
        names: dict[str, list[str]] = {}
        for key, labels in schema.items():
            if isinstance(labels, dict):
                labels = labels.get("labels", [key])
            if isinstance(labels, str):
                labels = [labels]
            names[str(key)] = [str(label) for label in labels] if labels else [str(key)]
        return names
    if isinstance(schema, (list, tuple)):
        return {str(key): [str(key)] for key in schema}

    # A CSV header is its own schema. For text documents, find simple labelled lines.
    if pages and pages[0][1].lstrip().startswith(("{", "[")):
        try:
            obj = json.loads(pages[0][1])
            if isinstance(obj, dict):
                return {str(k): [str(k)] for k in obj}
        except (json.JSONDecodeError, TypeError):
            pass
    names = {}
    if pages:
        first = pages[0][1]
        if "," in first.splitlines()[0] if first.splitlines() else False:
            try:
                header = next(csv.reader([first.splitlines()[0]]))
                names.update({key.strip(): [key.strip()] for key in header if key.strip()})
            except csv.Error:
                pass
        if not names:
            for line in first.splitlines():
                match = re.match(r"^\s*([\w][\w ./()#-]{0,80})\s*:\s*.*$", line)
                if match:
                    key = match.group(1).strip()
                    names.setdefault(key.lower().replace(" ", "_"), [key])
    return names


def _csv_engine(path: Path, pages: list[tuple[int, str]], schema: Any) -> dict[str, dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    names = _schema_names(schema, pages)
    if not rows:
        return {key: {"value": None, "page": 1, "confidence": 0.0} for key in names}
    row = rows[0]
    normalized = {str(key).strip().casefold(): value for key, value in row.items() if key is not None}
    result = {}
    for name, labels in names.items():
        value = next((normalized[label.strip().casefold()] for label in labels
                      if label.strip().casefold() in normalized), None)
        result[name] = {"value": value.strip() if isinstance(value, str) else value,
                        "page": 1, "confidence": 1.0 if value not in (None, "") else 0.0}
    return result


def _csv_grid_engine(pages: list[tuple[int, str]], schema: Any) -> dict[str, dict[str, Any]]:
    """Second CSV implementation: parse the extracted page grid independently."""
    text = pages[0][1] if pages else ""
    try:
        rows = list(csv.reader(text.splitlines()))
    except csv.Error:
        return {}
    names = _schema_names(schema, pages)
    if len(rows) < 2:
        return {key: {"value": None, "page": 1, "confidence": 0.0} for key in names}
    header = {key.strip().casefold(): index for index, key in enumerate(rows[0])}
    record = rows[1]
    output = {}
    for name, labels in names.items():
        index = next((header[label.strip().casefold()] for label in labels
                      if label.strip().casefold() in header), None)
        value = record[index].strip() if index is not None and index < len(record) else None
        output[name] = {"value": value or None, "page": 1, "confidence": 1.0 if value else 0.0}
    return output


def _label_engine(pages: list[tuple[int, str]], schema: Any) -> dict[str, dict[str, Any]]:
    names = _schema_names(schema, pages)
    result: dict[str, dict[str, Any]] = {}
    for name, labels in names.items():
        found = None
        for page, text in pages:
            lines = text.splitlines()
            # Prefer explicit inline labels, including labels embedded in a
            # sentence (common in government guides that show filled examples).
            for i, line in enumerate(lines):
                for label in labels:
                    match = re.search(rf"(?:^|\b){re.escape(label)}\s*[:=#]\s*(.*?)\s*$",
                                      line, re.IGNORECASE)
                    if not match and label.rstrip().endswith("#"):
                        match = re.search(rf"(?:^|\b){re.escape(label)}\s+(.+?)\s*$",
                                          line, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        if value:
                            found = {"value": value, "page": page, "confidence": 0.96}
                            break
                        for candidate in lines[i + 1:i + 7]:
                            candidate = candidate.strip()
                            # Multi-column PDF text extraction may put the
                            # label and its single-token example several lines
                            # apart. Ignore neighboring prose and bullets.
                            if (re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9,./#-]{1,40}", candidate)
                                    and (any(char.isupper() for char in candidate) or any(char.isdigit() for char in candidate))):
                                found = {"value": candidate, "page": page, "confidence": 0.82}
                                break
                        if found:
                            break
                if found:
                    break
            # If a schema supplies a literal value cue (rather than a field
            # heading), preserve that exact text as a candidate for review.
            if not found:
                for label in labels:
                    if label.casefold().replace(" ", "_") == name.casefold():
                        continue
                    for line in lines:
                        if re.search(rf"\b{re.escape(label)}\b", line, re.IGNORECASE):
                            found = {"value": label, "page": page, "confidence": 0.78}
                            break
                    if found:
                        break
            if found:
                break
        # Only after searching every page for an explicit label or a literal
        # value cue, use the weaker heading-on-one-line fallback.
        if not found:
            for page, text in pages:
                lines = text.splitlines()
                for i, line in enumerate(lines):
                    for label in labels:
                        if re.fullmatch(rf"\s*{re.escape(label)}\s*", line, re.IGNORECASE):
                            if i + 1 < len(lines) and lines[i + 1].strip():
                                found = {"value": lines[i + 1].strip(), "page": page, "confidence": 0.72}
                                break
                    if found:
                        break
                if found:
                    break
        result[name] = found or {"value": None, "page": None, "confidence": 0.0}
    return result


def _pdf_layout_engine(path: Path, schema: Any) -> dict[str, dict[str, Any]]:
    """Read single-token values aligned under or beside PDF table headings."""
    try:
        import pdfplumber
    except ImportError:
        return {}
    names = _schema_names(schema, [])
    if not names:
        return {}
    output: dict[str, dict[str, Any]] = {}
    try:
        with pdfplumber.open(path) as pdf:
            for name, labels in names.items():
                for page_no, page in enumerate(pdf.pages, 1):
                    words = page.extract_words()
                    rows: list[list[dict[str, Any]]] = []
                    for word in sorted(words, key=lambda item: (item["top"], item["x0"])):
                        row = next((items for items in rows if abs(items[0]["top"] - word["top"]) <= 2.0), None)
                        if row is None:
                            rows.append([word])
                        else:
                            row.append(word)
                    rows.sort(key=lambda items: items[0]["top"])
                    matched = False
                    for row_index, row in enumerate(rows):
                        row.sort(key=lambda item: item["x0"])
                        normalized_words = [re.sub(r"[^a-z0-9]+", "", item["text"].casefold())
                                            for item in row]
                        for label in labels:
                            label_words = [re.sub(r"[^a-z0-9]+", "", part.casefold())
                                           for part in re.findall(r"[\w#]+", label)]
                            if not label_words:
                                continue
                            for start in range(len(row) - len(label_words) + 1):
                                if normalized_words[start:start + len(label_words)] != label_words:
                                    continue
                                left = row[start]["x0"]
                                right = row[start + len(label_words) - 1]["x1"]
                                # Prefer a token immediately to the right on
                                # the same line, then a token below the heading
                                # inside its horizontal span.
                                has_inline_delimiter = row[start + len(label_words) - 1]["text"].endswith((":", "="))
                                hash_label = label.rstrip().endswith("#")
                                candidates = ([item for item in row[start + len(label_words):]
                                               if item["x0"] >= right and
                                               re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9,./#-]{1,40}", item["text"])]
                                              if has_inline_delimiter or hash_label else [])
                                if not candidates:
                                    for next_row in rows[row_index + 1:]:
                                        delta = next_row[0]["top"] - row[0]["top"]
                                        if delta > 32:
                                            break
                                        candidates = [item for item in next_row
                                                      if item["x0"] < right + 18 and item["x1"] > left - 4 and
                                                      re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9,./#-]{1,40}", item["text"])]
                                        if candidates:
                                            break
                                if candidates:
                                    chosen = min(candidates, key=lambda item: (abs(item["x0"] - left), item["x0"]))
                                    output[name] = {"value": chosen["text"].rstrip("."), "page": page_no,
                                                    "confidence": 0.90}
                                    matched = True
                                    break
                            if matched:
                                break
                        if matched:
                            break
                    if matched:
                        break
    except (OSError, RuntimeError):
        return output
    return output


def _ollama_engine(pages: list[tuple[int, str]], schema: Any) -> dict[str, dict[str, Any]]:
    names = _schema_names(schema, pages)
    if not names:
        return {}
    # Keep large public guides inside the local model context. Pages containing
    # requested labels are preferred; surrounding text remains available so the
    # model can interpret the source independently.
    labels = [label for field_labels in names.values() for label in field_labels]
    relevant = []
    for page, text in pages:
        if any(label.casefold() in text.casefold() for label in labels):
            relevant.append({"page": page, "text": text[:5000]})
    if not relevant:
        relevant = [{"page": page, "text": text[:3000]} for page, text in pages[:3]]
    document_pages = []
    remaining = 12000
    for page in relevant:
        clipped = page["text"][:remaining]
        if clipped:
            document_pages.append({"page": page["page"], "text": clipped})
            remaining -= len(clipped)
        if remaining <= 0:
            break
    prompt = {
        "task": "Extract only explicitly present values from this document. Do not infer or fill gaps.",
        "schema": {key: labels for key, labels in names.items()},
        "required_output": {"fields": {key: {"value": "string or null", "page": "1-based page or null"}
                                         for key in names}},
        "document_pages": document_pages,
    }
    payload = json.dumps({
        "model": os.environ.get("GLACIER_READER_MODEL", _MODEL_DEFAULT),
        "prompt": json.dumps(prompt, ensure_ascii=False),
        "stream": False,
        "format": "json",
        "options": {"temperature": 0, "num_ctx": 4096},
        "keep_alive": "10m",
    }).encode()
    request = urllib.request.Request(f"{_OLLAMA_URL}/api/generate", data=payload,
                                     headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=_MODEL_TIMEOUT) as response:
        response_body = json.loads(response.read())
    parsed = json.loads(response_body.get("response", "{}"))
    raw_fields = parsed.get("fields", parsed) if isinstance(parsed, dict) else {}
    output = {}
    for key in names:
        value = raw_fields.get(key, {}) if isinstance(raw_fields, dict) else {}
        if isinstance(value, dict):
            output[key] = {"value": value.get("value"), "page": value.get("page"), "confidence": 0.65}
        else:
            output[key] = {"value": value, "page": None, "confidence": 0.65}
    return output


def _ocr_engine(path: Path, pages: list[tuple[int, str]], schema: Any) -> dict[str, dict[str, Any]]:
    executable = shutil.which("tesseract")
    if not executable or path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}:
        return {}
    run = subprocess.run([executable, str(path), "stdout"], capture_output=True, text=True,
                         timeout=30, check=False)
    if run.returncode:
        return {}
    return _label_engine([(1, run.stdout)], schema)


def _available_engines() -> list[tuple[str, Any]]:
    return [("labels", _label_engine), ("ollama", _ollama_engine)]


def _read_pages(path: Path) -> list[tuple[int, str]]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        try:
            import pdfplumber
        except ImportError as exc:
            raise RuntimeError("Reading PDFs requires the installed pdfplumber package") from exc
        with pdfplumber.open(path) as pdf:
            return [(index, page.extract_text() or "") for index, page in enumerate(pdf.pages, 1)]
    if suffix in {".csv", ".tsv"}:
        delimiter = "\t" if suffix == ".tsv" else ","
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle, delimiter=delimiter))
        return [(1, "\n".join(delimiter.join(row) for row in rows))]
    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}:
        executable = shutil.which("tesseract")
        if executable:
            run = subprocess.run([executable, str(path), "stdout"], capture_output=True, text=True,
                                 timeout=30, check=False)
            if run.returncode == 0:
                return [(1, run.stdout)]
        return [(1, "")]
    return [(1, path.read_text(encoding="utf-8", errors="replace"))]


def _normalize(value: Any) -> str | None:
    if value is None:
        return None
    return re.sub(r"\s+", " ", str(value)).strip().casefold() or None


def read_document(path: str | os.PathLike[str], schema: Any = None) -> dict[str, Any]:
    """Read a PDF, image, CSV, TSV, JSON, or text file using two local engines.

    `schema` maps canonical field names to visible labels (or a list of labels).
    A field is certain only when the deterministic extractor and local model/OCR
    agree on its value. When the second engine is unavailable, the extracted
    value is retained but marked uncertain for human confirmation.
    """
    source = Path(path)
    pages = _read_pages(source)
    available = _available_engines()
    is_default_engine_list = (len(available) == 2 and available[0][1] is _label_engine
                              and available[1][1] is _ollama_engine)
    if is_default_engine_list:
        primary_engine = _csv_engine if source.suffix.lower() in {".csv", ".tsv"} else _label_engine
        secondary_engines = [_csv_grid_engine] if source.suffix.lower() in {".csv", ".tsv"} else [available[1][1]]
    else:
        # A replaceable engine list also makes deterministic independent-engine
        # testing possible without running a local model in every unit test.
        primary_engine = available[0][1] if available else _label_engine
        secondary_engines = [engine for _, engine in available[1:]]
    try:
        primary = primary_engine(source, pages, schema) if primary_engine is _csv_engine else primary_engine(pages, schema)
    except (OSError, urllib.error.URLError, TimeoutError, subprocess.SubprocessError,
            json.JSONDecodeError, RuntimeError):
        primary = {}
    if source.suffix.lower() == ".pdf" and primary_engine is _label_engine:
        # Text-flow parsing handles prose and explicit labels; coordinate-based
        # extraction handles compact table cells that flatten badly to text.
        layout = _pdf_layout_engine(source, schema)
        labels = _schema_names(schema, pages)
        for key, candidate in layout.items():
            current_value = primary.get(key, {}).get("value")
            label_values = {_normalize(label) for label in labels.get(key, [])}
            heading_cue = any(label.istitle() for label in labels.get(key, []))
            if current_value is None or (_normalize(current_value) in label_values and heading_cue):
                primary[key] = candidate

    secondary = {}
    for engine in secondary_engines:
        try:
            result = engine(pages, schema)
        except (OSError, urllib.error.URLError, TimeoutError, subprocess.SubprocessError,
                json.JSONDecodeError, RuntimeError):
            continue
        if result:
            secondary.update(result)

    names = _schema_names(schema, pages)
    if not names:
        names = {key: [key] for key in primary}
    fields: dict[str, dict[str, Any]] = {}
    for key in names:
        first = primary.get(key, {"value": None, "page": None, "confidence": 0.0})
        second = secondary.get(key)
        agrees = bool(second is not None and _normalize(first.get("value")) == _normalize(second.get("value"))
                      and _normalize(first.get("value")) is not None)
        fields[key] = {
            # A disputed candidate must not flow into a prepared filing as if
            # it were usable data. Keep only its source location for review.
            "value": first.get("value") if agrees or second is None else None,
            "page": first.get("page"),
            "confidence": min(float(first.get("confidence", 0.0)), float(second.get("confidence", 0.0)))
            if agrees else (float(first.get("confidence", 0.0)) * 0.5 if second is None else 0.0),
            "uncertain": not agrees,
        }
    return {"fields": fields, "text": "\n".join(text for _, text in pages)}
