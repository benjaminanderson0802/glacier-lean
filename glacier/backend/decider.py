"""Decide: pick exactly one option from a fixed list. Used by the Decide step in flows, and reusable by claim triage
and routing. Engines (free first, per the owner's model policy):
  - "local": an Ollama model with its output constrained to the option list (GLACIER_OLLAMA_URL, GLACIER_LOCAL_MODEL)
  - "codex": Codex CLI (default model from ~/.codex/config.toml, e.g. GPT-6 Luna) with a JSON schema for the answer
  - "auto":  local if Ollama answers, otherwise codex
A paid engine (OpenAI Decisions API) is deliberately absent: it needs an owner-approved proposal first."""
import json, os, subprocess, tempfile, urllib.request
import shell_commands
from egress import open_model_request

ENGINES = ("auto", "local", "codex")
MAX_OPTIONS = 12


def parse_options(text: str) -> list[str]:
    opts, seen = [], set()
    for o in str(text or "").replace("\n", ",").split(","):
        o = o.strip()
        if o and o.lower() not in seen:
            seen.add(o.lower()); opts.append(o)
    if len(opts) < 2:
        raise ValueError("a decision needs at least 2 options")
    if len(opts) > MAX_OPTIONS:
        raise ValueError(f"a decision allows at most {MAX_OPTIONS} options")
    return opts


def _prompt(question: str, options: list[str], context: str, include_reason: bool = False) -> str:
    answer = ('{"choice": <one option>, "reason": <brief evidence-based reason>}' if include_reason
              else '{"choice": <one option>}')
    return (f"{question.strip()}\n\nChoose exactly one of: {', '.join(options)}.\n"
            f"Answer with JSON {answer} and nothing else.\n\nContext:\n{context[-6000:] or '(none)'}")


def _schema(options, include_reason: bool = False):
    properties = {"choice": {"type": "string", "enum": options}}
    required = ["choice"]
    if include_reason:
        properties["reason"] = {"type": "string"}
        required.append("reason")
    return {"type": "object", "properties": properties, "required": required, "additionalProperties": False}


def _local(question, options, context, model, include_reason=False):
    url = os.environ.get("GLACIER_OLLAMA_URL", "http://localhost:11434").rstrip("/") + "/api/chat"
    body = {"model": model or __import__("system_check").default_local_model(), "stream": False, "think": False,
            "format": _schema(options, include_reason), "options": {"temperature": 0},
            "messages": [{"role": "user", "content": _prompt(question, options, context, include_reason)}]}
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with open_model_request(req, timeout=int(os.environ.get("GLACIER_DECIDE_TIMEOUT", "120"))) as r:
        content = json.loads(r.read())["message"]["content"]
    return json.loads(content), f"local model {body['model']}"


def _codex(question, options, context, model, include_reason=False):
    with tempfile.TemporaryDirectory() as d:
        schema, out = os.path.join(d, "schema.json"), os.path.join(d, "out.txt")
        with open(schema, "w") as f:
            json.dump(_schema(options, include_reason), f)
        args = shell_commands.executable_invocation(os.environ.get("CODEX_BIN", "codex"), "exec", "--skip-git-repo-check", "-s", "read-only", "-C", d,
                "--output-schema", schema, "-o", out) + (["-m", model] if model else []) + ["--", _prompt(question, options, context, include_reason)]
        p = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                           timeout=int(os.environ.get("GLACIER_DECIDE_TIMEOUT", "300")))
        if p.returncode != 0:
            raise RuntimeError(f"codex decide failed (exit {p.returncode}): {(p.stdout + p.stderr)[-300:]}")
        with open(out) as f:
            text = f.read().strip()
    return json.loads(text[text.find("{"): text.rfind("}") + 1]), "codex" + (f" {model}" if model else "")


def decide(question: str, options: list[str], context: str = "", engine: str = "auto", model: str = "") -> dict:
    """Returns {"choice": one of options (original spelling), "engine": what answered}. Raises if no valid answer."""
    if engine not in ENGINES:
        raise ValueError(f"unknown decision engine {engine!r} (use one of {', '.join(ENGINES)})")
    if not question.strip():
        raise ValueError("a decision needs a question")
    # Supervisor decisions need a recorded explanation when they disagree with
    # deterministic checks. Other callers retain the simple choice-only shape.
    include_reason = "provide an explicit reason grounded in the evidence" in question.lower()
    errors = []
    for eng in (["local", "codex"] if engine == "auto" else [engine]):
        try:
            answer, used = (_local if eng == "local" else _codex)(question, options, context, model, include_reason)
        except Exception as e:  # try the next engine in auto mode
            errors.append(f"{eng}: {e}")
            continue
        raw = answer.get("choice") if isinstance(answer, dict) else answer
        match = [o for o in options if o.lower() == str(raw).strip().lower()]
        if match:
            result = {"choice": match[0], "engine": used}
            if include_reason:
                reason = answer.get("reason", "") if isinstance(answer, dict) else ""
                result["reason"] = reason if isinstance(reason, str) else ""
            return result
        errors.append(f"{eng}: answer {raw!r} is not one of the options")
    raise RuntimeError("no valid decision: " + "; ".join(errors))
