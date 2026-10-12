"""Ask the configured free/local model routes for schema-checked JSON."""

import json

import gateway


def run(ctx):
    config = dict(ctx.get("config") or {})
    prompt = str(config.get("prompt") or "").strip()
    if not prompt:
        return {"state": "failed", "exit_code": 1, "output": "Add a question for the AI step"}
    schema_text = str(config.get("schema") or "").strip()
    if not schema_text:
        return {"state": "failed", "exit_code": 1, "output": "Add a JSON schema for the answer"}
    try:
        schema = json.loads(schema_text)
        if not isinstance(schema, dict):
            raise ValueError()
    except (ValueError, json.JSONDecodeError):
        return {"state": "failed", "exit_code": 1, "output": "The JSON schema must be a JSON object"}
    config["prompt"] = (prompt + "\n\nReturn only JSON that matches this JSON Schema:\n" +
                        json.dumps(schema, ensure_ascii=False, separators=(",", ":")))
    if str(config.get("engine") or "configured").strip().lower() == "codex":
        try:
            import runner
            timeout = max(1, min(int(config.get("timeout") or 600), 24 * 3600))
            result = runner.run_codex(ctx.get("env_id", ""), ctx.get("run_id", ""), ctx.get("node_id", ""),
                config, str((ctx.get("prev") or {}).get("output") or "")[-8000:], timeout, ctx.get("workspace", ""))
        except (RuntimeError, OSError, TypeError, ValueError) as exc:
            return {"state": "failed", "exit_code": 1, "output": str(exc)}
    else:
        result = gateway.complete({**ctx, "config": config})
    if result.get("state") != "done" or result.get("exit_code", 0) != 0:
        return result
    raw = str(result.get("output") or "").strip()
    if raw.startswith("codex exit ") and "\n" in raw:
        raw = raw.split("\n", 1)[1].strip()
    try:
        value, _ = json.JSONDecoder().raw_decode(raw.lstrip())
        from jsonschema import validate
        validate(value, schema)
    except Exception as exc:
        return {"state": "failed", "exit_code": 1,
                "output": f"The AI answer did not match the requested JSON format: {exc}"}
    result["output"] = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return result


NODE = {"catalog": {"type": "structured_ai", "label": "Ask AI for JSON",
    "description": "Ask an owner-configured model route or the signed-in Codex CLI for checked JSON data.",
    "worker": True, "fields": [
        {"key": "prompt", "label": "What should AI do?", "placeholder": "Classify this item: {prev_output}", "default": "", "multiline": True},
        {"key": "schema", "label": "Required JSON shape", "placeholder": '{"type":"object","properties":{"ok":{"type":"boolean"}},"required":["ok"]}', "default": '{"type":"object"}', "multiline": True},
        {"key": "engine", "label": "AI engine", "default": "configured", "options": ["configured", "codex"]},
        {"key": "routes", "label": "Model routes", "placeholder": "configured route names", "default": "", "optional": True},
        {"key": "timeout", "label": "Time limit (seconds)", "placeholder": "600", "default": "600", "optional": True},
        {"key": "retries", "label": "Retries if it fails", "placeholder": "0", "default": "0", "optional": True},
    ], "branches": None, "retry_safe": True}, "run": run}
