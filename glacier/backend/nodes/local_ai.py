"""Worker step that sends a prompt to an Ollama model running on the user's machine."""
import json
import os
import socket
import urllib.error
import urllib.request


DEFAULT_MODEL = "qwen3:0.6b"
DEFAULT_TIMEOUT = 600
PREV_LIMIT = 8000
ANSWER_ONLY_SYSTEM = "Reply with only the answer. No explanation, no labels, no markdown, no extra words."


def _clean_answer(output: str) -> str:
    single_line = "\n" not in output
    output = output.strip()
    if output.startswith("**") and output.endswith("**") and len(output) >= 4:
        output = output[2:-2].strip()
    elif (output.startswith("`") and output.endswith("`") and len(output) >= 2
          and not output.startswith("``")):
        output = output[1:-1].strip()
    if single_line and output.endswith("."):
        output = output[:-1]
    return output


def run(ctx: dict) -> dict:
    config = ctx["config"]
    prompt = (config.get("prompt") or "").strip()
    if not prompt:
        raise ValueError("Local AI needs a prompt")
    previous = ((ctx.get("prev") or {}).get("output") or "")[-PREV_LIMIT:]
    prompt = (prompt.replace("{env}", ctx["env_id"])
              .replace("{run}", ctx["run_id"])
              .replace("{prev_output}", previous))
    import system_check
    model = config.get("model") or system_check.default_local_model() or DEFAULT_MODEL
    try:
        timeout = int(config.get("timeout") or DEFAULT_TIMEOUT)
    except (TypeError, ValueError):
        timeout = DEFAULT_TIMEOUT
    timeout = max(1, min(timeout, 24 * 3600))
    base_url = os.environ.get("GLACIER_OLLAMA_URL", "http://localhost:11434").rstrip("/")
    url = base_url + "/api/chat"
    request = urllib.request.Request(
        url,
        data=json.dumps({
            "model": model,
            "messages": ([{"role": "system", "content": ANSWER_ONLY_SYSTEM}]
                         if config.get("answer_style", "Answer only") == "Answer only" else []) +
                        [{"role": "user", "content": prompt}],
            "stream": False,
            "think": False,
            **({"options": {"temperature": 0}}
               if config.get("answer_style", "Answer only") == "Answer only" else {}),
        }).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            reply = json.loads(response.read())
    except (socket.timeout, TimeoutError):
        return {
            "state": "failed",
            "exit_code": 1,
            "output": f"Local AI took longer than {timeout} seconds.",
        }
    except urllib.error.HTTPError:
        return {
            "state": "failed",
            "exit_code": 1,
            "output": f'Local AI could not use model "{model}". Download it with: ollama pull {model}.',
        }
    except (urllib.error.URLError, OSError):
        return {
            "state": "failed",
            "exit_code": 1,
            "output": f"Local AI is not running at {base_url}. Start Ollama, or pick another worker.",
        }
    message = reply.get("message") or {}
    output = message.get("content", "")
    if not isinstance(output, str):
        raise ValueError("Ollama returned an invalid reply")
    if config.get("answer_style", "Answer only") == "Answer only":
        output = _clean_answer(output)
    return {
        "state": "done",
        "exit_code": 0,
        "output": output,
        "usage": {
            "model": model,
            "route": "local/ollama",
            "tokens_in": int(reply.get("prompt_eval_count") or 0),
            "tokens_out": int(reply.get("eval_count") or 0),
            "generation_seconds": (float(reply.get("eval_duration") or 0) / 1_000_000_000),
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
            {"key": "answer_style", "label": "Answer style", "placeholder": "Answer only", "default": "Answer only", "optional": True,
             "options": ["Answer only", "Free text"]},
            {"key": "timeout", "label": "Time limit (seconds)", "placeholder": "600", "default": "600", "optional": True},
        ],
        "branches": None,
    },
    "run": run,
}
