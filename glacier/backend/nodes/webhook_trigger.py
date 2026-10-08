"""Local POST start. Request data is available to following steps as trigger_body."""


def run(ctx: dict) -> dict:
    body = (ctx.get("trigger") or {}).get("body")
    if body is None:
        raise ValueError("This step starts when called from this computer")
    import json
    return {"state": "done", "output": json.dumps(body, ensure_ascii=False, separators=(",", ":")), "exit_code": 0}


NODE = {
    "catalog": {
        "type": "webhook_trigger", "label": "When called from this computer",
        "description": "Start when a local tool sends a JSON request to this Environment.",
        "worker": True,
        "fields": [],
        "branches": None,
    },
    "run": run,
}
