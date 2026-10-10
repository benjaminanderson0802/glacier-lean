"""Local-first JSON, table, and CSV steps for everyday automations.

These adapters intentionally use Python's standard library: JSON, csv, and
SQLite are stable interchange formats and avoid adding runtime dependencies.
"""

import csv
import json
import os
import re
import sqlite3
import time
from pathlib import Path

_MAX_FILE_BYTES = 10 * 1024 * 1024
_MAX_ROWS = 100_000


def _done(value, message=""):
    return {"state": "done", "output": message or json.dumps(value, ensure_ascii=False), "exit_code": 0}


def _failed(message):
    return {"state": "failed", "output": f"error: {message}", "exit_code": 1}


def _previous(ctx):
    prev = ctx.get("prev") or {}
    text = prev.get("output", "")
    if not text:
        return None
    try:
        return json.loads(text)
    except (TypeError, json.JSONDecodeError):
        raise ValueError("The previous step did not return valid JSON") from None


def _json_config(config, key, default=None):
    value = config.get(key)
    if value in (None, ""):
        return default
    try:
        return json.loads(value) if isinstance(value, str) else value
    except json.JSONDecodeError:
        raise ValueError(f"{key.replace('_', ' ').capitalize()} must be valid JSON") from None


def _field(item, path):
    current = item
    for part in str(path).split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def run_json(ctx):
    config = ctx.get("config") or {}
    operation = str(config.get("operation") or "set_fields")
    try:
        value = _previous(ctx)
        if operation == "set_fields":
            fields = _json_config(config, "fields", {})
            if not isinstance(fields, dict):
                raise ValueError("Fields must be a JSON object")
            if isinstance(value, list):
                result = [{**item, **fields} if isinstance(item, dict) else item for item in value]
            else:
                result = {**(value if isinstance(value, dict) else {}), **fields}
        elif operation == "filter":
            if not isinstance(value, list):
                raise ValueError("The previous step must return a list to filter")
            target = _json_config(config, "equals", config.get("equals", ""))
            result = [item for item in value if str(_field(item, config.get("field", ""))) == str(target)]
        elif operation == "merge":
            addition = _json_config(config, "data", [] if isinstance(value, list) else {})
            if isinstance(value, dict) and isinstance(addition, dict):
                result = {**value, **addition}
            elif isinstance(value, list) and isinstance(addition, list):
                result = value + addition
            elif value is None:
                result = addition
            else:
                raise ValueError("Merge needs two objects or two lists")
        elif operation == "split":
            if isinstance(value, list):
                result = value
            elif isinstance(value, dict) and isinstance(value.get("items"), list):
                result = value["items"]
            else:
                raise ValueError("Split needs a list or an object with an items list")
        elif operation == "dedupe":
            if not isinstance(value, list):
                raise ValueError("The previous step must return a list to remove duplicates")
            key = str(config.get("key") or "")
            seen, result = set(), []
            for item in value:
                token = json.dumps(_field(item, key) if key else item, sort_keys=True, ensure_ascii=False)
                if token not in seen:
                    seen.add(token)
                    result.append(item)
        else:
            raise ValueError("Choose a supported JSON operation")
        return _done(result)
    except (ValueError, TypeError) as exc:
        return _failed(str(exc))


def _table_db(home):
    os.makedirs(home, exist_ok=True)
    db = os.path.join(home, "tables.sqlite")
    with sqlite3.connect(db, timeout=30) as conn:
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("CREATE TABLE IF NOT EXISTS automation_rows (table_name TEXT NOT NULL, row_key TEXT NOT NULL, body TEXT NOT NULL, PRIMARY KEY(table_name,row_key))")
    return db


def _table_source(home, table):
    return Path(home) / "tables" / f"{table}.json"


def _read_table_source(home, table):
    path = _table_source(home, table)
    try:
        records = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    except (OSError, json.JSONDecodeError):
        raise ValueError(f"The local table file for {table} could not be read") from None
    if not isinstance(records, list) or len(records) > _MAX_ROWS or any(not isinstance(row, dict) for row in records):
        raise ValueError(f"The local table file for {table} must be a JSON list of up to 100,000 rows")
    return records


def _write_table_source(home, table, records):
    path = _table_source(home, table)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _rebuild_table_index(conn, table, records):
    conn.execute("DELETE FROM automation_rows WHERE table_name=?", (table,))
    conn.executemany("INSERT INTO automation_rows(table_name,row_key,body) VALUES(?,?,?)",
        [(table, str(index), json.dumps(row, ensure_ascii=False)) for index, row in enumerate(records)])


def run_table(ctx):
    config = ctx.get("config") or {}
    table = str(config.get("table") or "").strip()
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,62}", table):
        return _failed("Use a table name with letters, numbers, underscores, or hyphens")
    operation = str(config.get("operation") or "query")
    try:
        db = _table_db(ctx["home"])
        records = _read_table_source(ctx["home"], table)
        with sqlite3.connect(db, timeout=30) as conn:
            _rebuild_table_index(conn, table, records)
            if operation in {"insert", "upsert"}:
                record = _json_config(config, "record", None)
                if record in (None, {}, ""):
                    record = _previous(ctx)
                if not isinstance(record, dict):
                    raise ValueError("Record must be a JSON object")
                key = str(config.get("key") or "").strip()
                if not key or key not in record or record[key] in (None, ""):
                    raise ValueError("Choose a key field that has a value in this record")
                if operation == "insert":
                    if any(str(row.get(key)) == str(record[key]) for row in records):
                        raise ValueError("A row with this key already exists")
                    records.append(record)
                else:
                    match = next((index for index, row in enumerate(records) if str(row.get(key)) == str(record[key])), None)
                    if match is None:
                        records.append(record)
                    else:
                        records[match] = record
                if len(records) > _MAX_ROWS:
                    raise ValueError("This table has more than 100,000 rows")
                _write_table_source(ctx["home"], table, records)
                _rebuild_table_index(conn, table, records)
                return _done(record)
            if operation == "query":
                match = _json_config(config, "match", {})
                if not isinstance(match, dict):
                    raise ValueError("Match must be a JSON object")
                result = [row for row in records if all(str(row.get(k)) == str(v) for k, v in match.items())]
                return _done(result)
            if operation == "dedupe":
                value = _previous(ctx)
                rows = value if value is not None else records
                if not isinstance(rows, list):
                    raise ValueError("Dedupe needs a list from the previous step")
                key = str(config.get("key") or "")
                seen, unique = set(), []
                for row in rows:
                    token = json.dumps(_field(row, key) if key else row, sort_keys=True, ensure_ascii=False)
                    if token not in seen:
                        seen.add(token)
                        unique.append(row)
                return _done({"rows": unique, "removed": len(rows) - len(unique)})
            raise ValueError("Choose insert, upsert, query, or dedupe")
    except (ValueError, TypeError, sqlite3.IntegrityError) as exc:
        return _failed(str(exc))


def _workspace_file(ctx, relative):
    root = Path(ctx.get("workspace") or Path(ctx["home"]) / "workspaces" / ctx.get("env_id", "default")).resolve()
    path = (root / str(relative or "")).resolve()
    if path != root and root not in path.parents:
        raise ValueError("Choose a file inside this flow's folder")
    return root, path


def run_csv(ctx):
    config = ctx.get("config") or {}
    try:
        root, path = _workspace_file(ctx, config.get("path"))
        operation = str(config.get("operation") or "read")
        if operation == "write":
            rows = _json_config(config, "data", None)
            if rows in (None, [], ""):
                rows = _previous(ctx)
            if isinstance(rows, dict):
                rows = [rows]
            if not isinstance(rows, list) or len(rows) > _MAX_ROWS or any(not isinstance(row, dict) for row in rows):
                raise ValueError("CSV writing needs a JSON list of row objects (up to 100,000 rows)")
            if not rows:
                raise ValueError("Add at least one row before writing a CSV file")
            root.mkdir(parents=True, exist_ok=True)
            headers = list(dict.fromkeys(key for row in rows for key in row.keys()))
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=headers, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)
            return _done(rows, f"Wrote {len(rows)} rows to {path.name}")
        if operation == "read":
            if not path.is_file():
                raise ValueError("The CSV file was not found in this flow's folder")
            if path.stat().st_size > _MAX_FILE_BYTES:
                raise ValueError("This CSV file is larger than 10 MB")
            with path.open("r", newline="", encoding="utf-8-sig") as stream:
                rows = list(csv.DictReader(stream))
            if len(rows) > _MAX_ROWS:
                raise ValueError("This CSV file has more than 100,000 rows")
            return _done(rows)
        raise ValueError("Choose read or write")
    except (OSError, ValueError, TypeError, csv.Error) as exc:
        return _failed(str(exc))


def run_delay(ctx):
    try:
        seconds = max(0, min(float((ctx.get("config") or {}).get("seconds", 1)), 3600))
        time.sleep(seconds)
        return {"state": "done", "output": str(((ctx.get("prev") or {}).get("output")) or "Wait finished"), "exit_code": 0}
    except (TypeError, ValueError) as exc:
        return _failed(f"Choose a wait time from 0 to 3,600 seconds ({exc})")


def _fields_for(kind, operation):
    if kind == "json_transform":
        return [
            {"key": "operation", "label": "Operation", "placeholder": "", "default": "set_fields",
             "options": ["set_fields", "filter", "merge", "split", "dedupe"]},
            {"key": "fields", "label": "Fields to set (JSON)", "placeholder": '{"status":"ready"}', "default": "{}", "multiline": True},
            {"key": "field", "label": "Field to check", "placeholder": "status", "default": "", "optional": True},
            {"key": "equals", "label": "Matches", "placeholder": "ready", "default": "", "optional": True},
            {"key": "data", "label": "Extra data (JSON)", "placeholder": "{}", "default": "", "optional": True, "multiline": True},
            {"key": "key", "label": "Unique field", "placeholder": "id", "default": "", "optional": True},
        ] + [{"key": "retries", "label": "Retries if it fails", "placeholder": "0", "default": "0", "optional": True}]
    if kind == "table":
        return [
            {"key": "table", "label": "Table name", "placeholder": "customers", "default": "customers"},
            {"key": "operation", "label": "Operation", "placeholder": "", "default": "upsert",
             "options": ["insert", "upsert", "query", "dedupe"]},
            {"key": "key", "label": "Unique field", "placeholder": "email", "default": "id", "optional": True},
            {"key": "record", "label": "Row (JSON)", "placeholder": '{"id":1,"name":"Ada"}', "default": "", "optional": True, "multiline": True},
            {"key": "match", "label": "Find rows (JSON)", "placeholder": '{"status":"new"}', "default": "{}", "optional": True, "multiline": True},
        ] + [{"key": "retries", "label": "Retries if it fails", "placeholder": "0", "default": "0", "optional": True}]
    return [
        {"key": "operation", "label": "Operation", "placeholder": "", "default": "read", "options": ["read", "write"]},
        {"key": "path", "label": "CSV file", "placeholder": "contacts.csv", "default": "contacts.csv"},
        {"key": "data", "label": "Rows to write (JSON)", "placeholder": '[{"name":"Ada"}]', "default": "", "optional": True, "multiline": True},
    ] + [{"key": "retries", "label": "Retries if it fails", "placeholder": "0", "default": "0", "optional": True}]


JSON_NODE = {"catalog": {"type": "json_transform", "label": "Change JSON", "description": "Set fields, filter, merge, split, or remove duplicate items.", "fields": _fields_for("json_transform", ""), "branches": None, "worker": True, "retry_safe": True}, "run": run_json}
TABLE_NODE = {"catalog": {"type": "data_table", "label": "Local table", "description": "Save, update, find, and deduplicate rows on this computer.", "fields": _fields_for("table", ""), "branches": None, "worker": True, "retry_safe": True}, "run": run_table}
CSV_NODE = {"catalog": {"type": "csv_file", "label": "Read or write CSV", "description": "Read or write a CSV file inside this flow's folder.", "fields": _fields_for("csv", ""), "branches": None, "worker": True, "retry_safe": True}, "run": run_csv}
DELAY_NODE = {"catalog": {"type": "delay", "label": "Wait", "description": "Pause this flow for a chosen time.", "fields": [
    {"key": "seconds", "label": "Seconds", "placeholder": "30", "default": "30"},
    {"key": "retries", "label": "Retries if it fails", "placeholder": "0", "default": "0", "optional": True}], "branches": None, "worker": True, "retry_safe": True}, "run": run_delay}
