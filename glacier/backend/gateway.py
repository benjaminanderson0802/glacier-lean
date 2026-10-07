"""Small OpenAI-compatible model router with local daily quota tracking."""
import json
import socket
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import claims

FRIENDLY_FAILURE = "No free model is available right now. A paid option needs your approval (a claim was filed)."
DEFAULT_ROUTE = {
    "name": "local",
    "base_url": "http://localhost:11434/v1",
    "model": "qwen3:0.6b",
    "paid": False,
    "daily_request_cap": 0,
}


def routes(home: str | Path) -> list[dict]:
    """Load route definitions, using local Ollama when gateway.json is absent."""
    path = Path(home) / "gateway.json"
    if not path.exists():
        return [dict(DEFAULT_ROUTE)]
    try:
        with path.open(encoding="utf-8") as stream:
            value = json.load(stream)
        if not isinstance(value, list):
            raise ValueError("it must contain a list of model routes")
        for index, route in enumerate(value):
            if not isinstance(route, dict):
                raise ValueError(f"route {index + 1} must be an object")
            missing = [key for key in ("name", "base_url", "model") if not isinstance(route.get(key), str) or not route[key].strip()]
            if missing:
                raise ValueError(f"route {index + 1} needs {', '.join(missing)}")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"Your model settings file (gateway.json) can't be read: {exc}") from None
    return value


def _usage_path(home: str | Path) -> Path:
    return Path(home) / "gateway_usage.json"


def _read_usage(home: str | Path) -> dict:
    try:
        with _usage_path(home).open(encoding="utf-8") as stream:
            value = json.load(stream)
        return value if isinstance(value, dict) else {}
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, OSError):
        return {}


def _daily_count(home: str | Path, name: str, today: str) -> int:
    entry = _read_usage(home).get(name, {})
    if not isinstance(entry, dict) or entry.get("date") != today:
        return 0
    return int(entry.get("requests", 0) or 0)


def _record_request(home: str | Path, name: str, today: str) -> None:
    path = _usage_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _read_usage(home)
    entry = data.get(name, {})
    count = int(entry.get("requests", 0) or 0) if isinstance(entry, dict) and entry.get("date") == today else 0
    data[name] = {"date": today, "requests": count + 1}
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _post(route: dict, prompt: str, timeout: int) -> dict:
    endpoint = route["base_url"].rstrip("/") + "/chat/completions"
    body = json.dumps({
        "model": route["model"],
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }).encode()
    request = urllib.request.Request(endpoint, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        result = json.loads(response.read())
    content = result["choices"][0]["message"]["content"]
    if not isinstance(content, str):
        raise ValueError("Model returned invalid chat content")
    return {"content": content, "response": result}


def complete(ctx: dict, routes: list[dict] | None = None, timeout: int | None = None) -> dict:
    """Try eligible routes in order and report the route that answered."""
    config = ctx.get("config") or {}
    try:
        route_list = routes if routes is not None else globals()["routes"](ctx["home"])
    except ValueError as exc:
        return {"state": "failed", "exit_code": 1, "output": str(exc)}
    selected = config.get("routes")
    if selected:
        names = {part.strip() for part in selected.split(",") if part.strip()}
        route_list = [route for route in route_list if route.get("name") in names]
    prompt = (config.get("prompt") or "").strip()
    previous = ((ctx.get("prev") or {}).get("output") or "")[-8000:]
    prompt = prompt.replace("{env}", str(ctx.get("env_id", "")))
    prompt = prompt.replace("{run}", str(ctx.get("run_id", "")))
    prompt = prompt.replace("{prev_output}", previous)
    try:
        request_timeout = int(timeout if timeout is not None else config.get("timeout") or 600)
    except (TypeError, ValueError):
        request_timeout = 600
    request_timeout = max(1, min(request_timeout, 24 * 3600))
    today = datetime.now(timezone.utc).date().isoformat()
    paid_blocked = False
    failures = []
    for route in route_list:
        if route.get("paid", True) is not False:
            paid_blocked = True
            continue
        cap = int(route.get("daily_request_cap", 0) or 0)
        if cap > 0 and _daily_count(ctx["home"], route["name"], today) >= cap:
            continue
        try:
            reply = _post(route, prompt, request_timeout)
        except (urllib.error.URLError, urllib.error.HTTPError, socket.timeout, TimeoutError, OSError, ValueError, KeyError) as exc:
            failures.append(f"{route.get('name', 'unnamed')}: {exc}")
            continue
        _record_request(ctx["home"], route["name"], today)
        result = reply["response"]
        usage = result.get("usage") or {}
        return {
            "state": "done",
            "exit_code": 0,
            "output": reply["content"],
            "usage": {
                "model": str(result.get("model") or route.get("model", "")),
                "route": f"gateway/{route['name']}",
                "tokens_in": int(usage.get("prompt_tokens", usage.get("input_tokens", 0)) or 0),
                "tokens_out": int(usage.get("completion_tokens", usage.get("output_tokens", 0)) or 0),
                "cost_usd": 0.0,
            },
        }
    if paid_blocked:
        summary = "Paid model route needs owner approval"
        today_utc = datetime.now(timezone.utc).date().isoformat()
        existing = claims.list_claims(status="filed")
        already_filed = any(
            claim.get("kind") == "policy"
            and claim.get("summary") == summary
            and (claim.get("updated") or "").startswith(today_utc)
            for claim in existing
        )
        if not already_filed:
            claims.file_claim(
                kind="policy",
                summary=summary,
                evidence="A workflow had no available free model route. D4 sets the paid route cap to $0; owner approval is required before any paid route can be used.",
                run_id=ctx.get("run_id", ""),
                node_id=ctx.get("node_id", ""),
            )
        output = FRIENDLY_FAILURE
    else:
        output = "No free model is available right now. Check that a model is running and try again."
        if failures:
            output += " " + failures[-1].split(":", 1)[0] + " could not be reached."
    return {"state": "failed", "exit_code": 1, "output": output}
