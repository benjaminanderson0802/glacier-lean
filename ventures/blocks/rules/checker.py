from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any


RULESETS = Path(__file__).with_name("rulesets")


def _load(ruleset: str | Path | dict[str, Any]) -> dict[str, Any]:
    if isinstance(ruleset, dict):
        return ruleset
    path = Path(ruleset)
    if not path.is_absolute():
        path = RULESETS / path
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml
        except ImportError as exc:
            raise RuntimeError("YAML rulesets require PyYAML") from exc
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    return json.loads(path.read_text(encoding="utf-8"))


def _value_at(fields: dict[str, Any], path: str) -> tuple[bool, Any]:
    current: Any = fields
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return False, None
        current = current[part]
    return True, current


def _valid(value: Any, rule: dict[str, Any]) -> bool:
    kind = rule.get("check", "non_empty")
    if kind == "non_empty":
        return value is not None and bool(str(value).strip())
    if kind == "non_empty_list":
        return isinstance(value, list) and bool(value) and all(str(v).strip() for v in value)
    if kind == "cpsc_citation_codes":
        if not isinstance(value, list) or not value:
            return False
        for item in value:
            code = re.sub(r"^\s*16\s+CFR\s+(?:part\s+)?", "", str(item), flags=re.IGNORECASE).strip()
            if not 3 <= len(code) <= 14 or re.search(r"\s", code):
                return False
        return True
    if kind == "enum_list":
        return isinstance(value, list) and bool(value) and all(v in rule.get("values", []) for v in value)
    if kind == "object_fields":
        return isinstance(value, dict) and all(
            key in value and value[key] is not None and bool(str(value[key]).strip())
            for key in rule.get("keys", []))
    if kind == "mapping_to_non_empty_lists":
        return isinstance(value, dict) and bool(value) and all(
            isinstance(items, list) and bool(items) and all(str(item).strip() for item in items)
            for items in value.values())
    if kind == "date":
        if not isinstance(value, str):
            return False
        try:
            date.fromisoformat(value.strip())
            return True
        except ValueError:
            return bool(re.fullmatch(r"(?:0[1-9]|1[0-2])/\d{2}/\d{4}", value.strip()))
    if kind == "date_month":
        return isinstance(value, str) and bool(re.fullmatch(
            r"(?:\d{4}-(0[1-9]|1[0-2])|(0[1-9]|1[0-2])/\d{4})", value.strip()))
    if kind == "phone":
        return isinstance(value, str) and len(re.sub(r"\D", "", value)) >= 7
    if kind == "enum":
        return value in rule.get("values", [])
    if kind == "pattern":
        return isinstance(value, str) and re.fullmatch(rule["pattern"], value.strip()) is not None
    return False


def check(fields: dict[str, Any], ruleset: str | Path | dict[str, Any]) -> dict[str, Any]:
    """Check fields against a named JSON/YAML rule set and cite each result."""
    spec = _load(ruleset)
    source = spec.get("source", {})
    default_cite = source.get("url", "")
    source_name = source.get("title", "Official source")
    results = []
    for rule in spec.get("rules", []):
        path = rule["field"]
        present, value = _value_at(fields, path)
        if not present:
            verdict = "uncertain"
            detail = f"No value was provided for {path}; confirm it from the source document."
        elif isinstance(value, dict) and "value" in value and "uncertain" in value:
            if value.get("uncertain") or value.get("value") is None:
                verdict = "uncertain"
                detail = f"The reader marked {path} as missing or needing confirmation."
            elif not _valid(value.get("value"), rule):
                verdict = "fail"
                detail = rule.get("failure", f"{path} does not meet the documented field requirement.")
            else:
                verdict = "pass"
                detail = rule.get("success", f"{path} is present in the expected form.")
        elif not _valid(value, rule):
            verdict = "fail"
            detail = rule.get("failure", f"{path} does not meet the documented field requirement.")
        else:
            verdict = "pass"
            detail = rule.get("success", f"{path} is present in the expected form.")
        cite = rule.get("cite", default_cite)
        if rule.get("section"):
            cite_title = rule.get("cite_title", source_name)
            cite = f"{cite_title}, {rule['section']} — {cite}"
        results.append({"rule": rule["id"], "verdict": verdict, "cite": cite, "detail": detail})
    verdicts = {item["verdict"] for item in results}
    overall = "fail" if "fail" in verdicts else "uncertain" if "uncertain" in verdicts else "pass"
    return {"verdict": overall, "results": results}
