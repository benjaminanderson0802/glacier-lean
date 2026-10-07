"""Worker step that sends a prompt to an Ollama model running on the user's machine."""
import json
import os
import urllib.error
import urllib.request


DEFAULT_MODEL = "qwen3:0.6b"
DEFAULT_TIMEOUT = 600
PREV_LIMIT = 8000


def run(ctx: dict) -> dict:
    config = ctx["config"]
    prompt = (config.get("prompt") or "").strip()
    if not prompt:
        raise ValueError("Local AI needs a prompt")
    previous = ((ctx.get("prev") or {}).get("output") or "")[-PREV_LIMIT:]
    prompt = (prompt.replace("{env}", ctx["env_id"])
              .replace("{run}", ctx["run_id"])
              .replace("{prev_output}", previous))
    model = config.get("model") or os.environ.get("GLACIER_LOCAL_MODEL") or DEFAULT_MODEL
    timeout = max(1, min(int(config.get("timeout") or DEFAULT_TIMEOUT), 24 * 3600))
    base_url = os.environ.get("GLACIER_OLLAMA_URL", "http://localhost:11434").rstrip("/")
    url = base_url + "/api/chat"
    request = urllib.request.Request(
        url,
        data=json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "think": False,
        }).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            reply = json.loads(response.read())
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        # HTTP errors are not a connection failure (for example, an unknown model).
        if isinstance(exc, urllib.error.HTTPError):
            raise RuntimeError(f"Ollama returned HTTP {exc.code}") from exc
        return {
            "state": "failed",
            "exit_code": 1,
            "output": f"Local AI is not running at {base_url}. Start Ollama, or pick another worker.",
        }
    message = reply.get("message") or {}
    output = message.get("content", "")
    if not isinstance(output, str):
        raise ValueError("Ollama returned an invalid reply")
    return {
        "state": "done",
        "exit_code": 0,
        "output": output,
        "usage": {
            "model": model,
            "route": "local/ollama",
            "tokens_in": int(reply.get("prompt_eval_count") or 0),
            "tokens_out": int(reply.get("eval_count") or 0),
            "cost_usd": 0.0,
        },
    }


NODE = {
    "catalog": {
        "type": "local_ai",
        "label": "Local AI",
        "description": "Hands a task to a model running on your computer through Ollama.",
        "worker": True,
        "fields": [
            {"key": "prompt", "label": "Task ({env} {run} {prev_output})", "placeholder": "Summarize: {prev_output}", "default": "", "multiline": True},
            {"key": "model", "label": "Model", "placeholder": "default local model", "default": "", "optional": True},
            {"key": "timeout", "label": "Time limit (seconds)", "placeholder": "600", "default": "600", "optional": True},
        ],
        "branches": None,
    },
    "run": run,
}
