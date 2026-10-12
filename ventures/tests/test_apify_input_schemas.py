"""Cross-venture Apify input schema rules verified against live deployment failures."""
import json
from pathlib import Path


VENTURES = Path(__file__).resolve().parents[1]


def _reject_duplicate_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AssertionError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _walk(node, path="$", errors=None):
    errors = errors if errors is not None else []
    if not isinstance(node, dict):
        return errors
    if node.get("type") == "array" and node.get("editor") != "json":
        errors.append(f"{path}: array property must set editor=json")
    items = node.get("items")
    if isinstance(items, dict) and isinstance(items.get("properties"), dict):
        for name, schema in items["properties"].items():
            if isinstance(schema, dict) and not schema.get("title"):
                errors.append(f"{path}.items.properties.{name}: nested item property needs a title")
    for key, value in node.items():
        if isinstance(value, dict):
            _walk(value, f"{path}.{key}", errors)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                _walk(child, f"{path}.{key}[{index}]", errors)
    return errors


def test_all_venture_apify_input_schemas_follow_apify_editor_rules():
    schemas = sorted(VENTURES.glob("**/.actor/input_schema.json"))
    assert schemas, "expected at least one Apify input schema"
    failures = []
    for path in schemas:
        try:
            schema = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_pairs)
        except (json.JSONDecodeError, AssertionError) as exc:
            failures.append(f"{path.relative_to(VENTURES)}: {exc}")
            continue
        if "editor" in schema:
            failures.append(f"{path.relative_to(VENTURES)}: top-level editor is unsupported")
        failures.extend(f"{path.relative_to(VENTURES)}: {error}" for error in _walk(schema))
    assert not failures, "\n".join(failures)
