"""Authenticated local webhook trigger routes."""

import json
import re

from fastapi import APIRouter, HTTPException, Request

import runner

router = APIRouter()
MAX_BODY = 1024 * 1024
_SECRET_KEY = re.compile(r"(?:secret|token|password|credential|api[_-]?key)", re.I)


def _scrub(value):
    if isinstance(value, dict):
        return {key: "[redacted]" if _SECRET_KEY.search(str(key)) else _scrub(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_scrub(item) for item in value]
    return value


@router.post("/api/hooks/{env_id}", status_code=202)
async def call_local_hook(env_id: str, request: Request):
    try:
        env = runner.load_env(env_id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(404, "Environment not found") from None
    if env.get("enabled", True) is False:
        raise HTTPException(409, "This Environment is paused")
    node = next((n for n in env.get("nodes", []) if n.get("type") == "webhook_trigger"), None)
    if not node:
        raise HTTPException(404, "This Environment has no local call start")
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type != "application/json":
        raise HTTPException(415, "Send a JSON body")
    chunks = bytearray()
    async for chunk in request.stream():
        chunks.extend(chunk)
        if len(chunks) > MAX_BODY:
            raise HTTPException(413, "The JSON body is too large")
    try:
        body = json.loads(chunks or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(400, "The body must be valid JSON") from None
    body = _scrub(body)
    run_id = runner.start_run(env_id, {"_trigger": {"type": "webhook", "node_id": node["id"], "body": body}})
    return {"run_id": run_id}
