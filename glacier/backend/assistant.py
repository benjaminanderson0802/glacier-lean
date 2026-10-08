"""The assistant's planner (roadmap: goal -> proposed flow + acceptance checks shown before running).
It only PROPOSES: the owner reviews the plan, and saving/running goes through the same API and approvals as the owner
(rule: the assistant edits flows only through the same API; every save is a git commit).
Engines are free (owner policy): "codex" (Codex CLI default model, structured output) or "local" (Ollama, JSON schema).
A plan that fails validation gets exactly one repair attempt with the errors (self-fix budget), then the errors are shown."""
import json, os, re, subprocess, tempfile, urllib.request
import verify
import shell_commands
from egress import open_model_request

MAX_STEPS = 12


def _schema(types: list[str]) -> dict:
    node = {"type": "object", "additionalProperties": False, "required": ["id", "type", "config"],
            "properties": {"id": {"type": "string"}, "type": {"type": "string", "enum": types},
                           "config": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                                      "required": ["key", "value"], "properties": {"key": {"type": "string"}, "value": {"type": "string"}}}}}}
    edge = {"type": "object", "additionalProperties": False, "required": ["source", "target", "label"],
            "properties": {"source": {"type": "string"}, "target": {"type": "string"}, "label": {"type": "string"}}}
    check = {"type": "object", "additionalProperties": False, "required": ["kind", "cmd", "question", "rubric"],
             "properties": {"kind": {"type": "string", "enum": list(verify.KINDS)}, "cmd": {"type": "string"},
                            "question": {"type": "string"}, "rubric": {"type": "string"}}}
    return {"type": "object", "additionalProperties": False,
            "required": ["name", "explanation", "nodes", "edges", "acceptance"],
            "properties": {"name": {"type": "string"}, "explanation": {"type": "string"},
                           "nodes": {"type": "array", "items": node, "maxItems": MAX_STEPS},
                           "edges": {"type": "array", "items": edge}, "acceptance": {"type": "array", "items": check, "minItems": 1}}}


def _prompt(goal: str, catalog: list[dict], errors: str = "") -> str:
    kinds = "\n".join(f"- {t['type']} ({t['label']}): {t.get('description', '')} settings: "
                      + ", ".join(f['key'] for f in t.get('fields', []))
                      + (f"; arrows labelled {t['branches'][0]}/{t['branches'][1]}" if t.get('branches') else "")
                      + ("; arrows labelled with its own options" if t.get('branches_from') == 'options' else "")
                      for t in catalog)
    text = ("You plan automations for Glacier. Turn the goal into a small flow of steps (at most 12) using ONLY these step "
            f"types:\n{kinds}\n\nRules: prefer simple steps; any step that changes files, sends, publishes or deletes must come "
            "after an approval step's 'yes' arrow; AI work uses codex (or local_ai if available); end with a note step that "
            "records the result. Always add at least one acceptance check that proves the goal is done (kind command with cmd, "
            "or rubric with rubric, or human with question; leave unused fields empty). The explanation is 2-4 plain sentences "
            "for a non-technical person.\n\nGoal: " + goal)
    if errors:
        text += "\n\nYour previous plan had these problems; fix them all:\n" + errors
    return text


def _ask_codex(prompt: str, schema: dict) -> dict:
    with tempfile.TemporaryDirectory() as d:
        sp, out = os.path.join(d, "schema.json"), os.path.join(d, "out.txt")
        json.dump(schema, open(sp, "w"))
        args = shell_commands.executable_invocation(os.environ.get("GLACIER_PLANNER_BIN") or os.environ.get("CODEX_BIN", "codex"), "exec", "--json",
                "--skip-git-repo-check", "-s", "read-only", "-C", d, "--output-schema", sp, "-o", out, "--", prompt)
        p = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=600)
        if not os.path.exists(out):
            raise RuntimeError(f"the planner did not answer (exit {p.returncode}): {(p.stdout + p.stderr)[-300:]}")
        text = open(out).read()
    return json.loads(text[text.find("{"): text.rfind("}") + 1])


def _ask_local(prompt: str, schema: dict) -> dict:
    url = os.environ.get("GLACIER_OLLAMA_URL", "http://localhost:11434").rstrip("/") + "/api/chat"
    body = {"model": __import__("system_check").default_local_model(), "stream": False, "think": False, "format": schema,
            "options": {"temperature": 0}, "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with open_model_request(req, timeout=600) as r:
        return json.loads(json.loads(r.read())["message"]["content"])


def _normalize(plan: dict) -> dict:
    """Structured output gives settings as [{key, value}] (strict schemas cannot have free-form objects)."""
    for n in plan.get("nodes", []):
        c = n.get("config")
        if isinstance(c, list):
            n["config"] = {i.get("key"): i.get("value", "") for i in c if isinstance(i, dict) and i.get("key")}
    return plan


def validate(plan: dict, catalog: list[dict]) -> list[str]:
    plan = _normalize(plan)
    errs, by_type = [], {t["type"]: t for t in catalog}
    ids = [n.get("id") for n in plan.get("nodes", [])]
    if not ids:
        errs.append("the flow has no steps")
    if len(set(ids)) != len(ids):
        errs.append("step ids must be unique")
    nodes = {n["id"]: n for n in plan.get("nodes", []) if n.get("id")}
    for n in plan.get("nodes", []):
        t = by_type.get(n.get("type"))
        if not t:
            errs.append(f"step {n.get('id')}: unknown type {n.get('type')!r}")
            continue
        allowed = {f["key"] for f in t.get("fields", [])}
        extra = set((n.get("config") or {})) - allowed
        if extra:
            errs.append(f"step {n['id']} ({n['type']}): unknown settings {sorted(extra)}; allowed: {sorted(allowed)}")
    for e in plan.get("edges", []):
        if e.get("source") not in nodes or e.get("target") not in nodes:
            errs.append(f"arrow {e.get('source')} -> {e.get('target')} points to a missing step")
            continue
        src = nodes[e["source"]]
        t = by_type.get(src.get("type"), {})
        labels = t.get("branches") or ([o.strip() for o in (src.get("config") or {}).get("options", "").split(",") if o.strip()]
                                       if t.get("branches_from") == "options" else None)
        if labels and e.get("label") and e["label"].lower() not in [l.lower() for l in labels]:
            errs.append(f"arrow from {src['id']} has label {e['label']!r}; use one of {labels}")
    acc = [{k: v for k, v in c.items() if v} for c in plan.get("acceptance", [])]
    try:
        verify.validate(acc)
        if not acc:
            errs.append("add at least one acceptance check")
    except ValueError as ex:
        errs.append(str(ex))
    return errs


def to_flow(plan: dict, flow_id: str, goal: str) -> dict:
    order = [n["id"] for n in plan["nodes"]]
    return {"id": flow_id, "name": plan.get("name") or flow_id, "goal": goal,
            "nodes": [{"id": n["id"], "type": n["type"], "config": dict(n.get("config") or {}),
                       "position": {"x": 60 + 260 * (i % 4), "y": 60 + 140 * (i // 4)}} for i, n in enumerate(plan["nodes"])],
            "edges": [{"id": f"e{i + 1}", "source": e["source"], "target": e["target"], "label": e.get("label", "")}
                      for i, e in enumerate(plan.get("edges", []))],
            "acceptance": [{k: v for k, v in c.items() if v} for c in plan.get("acceptance", [])],
            "created_by": "assistant"}


def plan(goal: str, catalog: list[dict], flow_id: str, engine: str = "codex", context: str = "") -> dict:
    """Returns {"flow", "explanation", "problems"}; problems is empty when the plan is ready to review and save."""
    if not goal.strip():
        raise ValueError("describe the goal first")
    schema = _schema([t["type"] for t in catalog if t["type"] != "schedule"] + ["schedule"])
    errors, p = "", {}
    for _ in range(2):  # one repair attempt (self-fix budget)
        prompt = _prompt(f"{context}{goal}" if context else goal, catalog, errors)
        if engine == "local":
            p = _ask_local(prompt, schema)
        elif engine == "codex":
            p = _ask_codex(prompt, schema)
        else:
            # Reuse Ask's official CLI/API adapters so the selected engine also handles
            # proposals; provider-specific credentials and outbound rules stay centralized.
            from routes import assistant_chat
            request = prompt + "\n\nReturn only the requested JSON object and no surrounding text."
            answer = assistant_chat._ask_engine(request, engine, schema=schema)
            try:
                raw = answer.get("reply", "")
                p = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
            except (ValueError, TypeError):
                p = {}
        p = _normalize(p)
        problems = validate(p, catalog)
        if not problems:
            return {"flow": to_flow(p, flow_id, goal), "explanation": p.get("explanation", ""), "problems": []}
        errors = "\n".join(f"- {x}" for x in problems)
    return {"flow": to_flow(p, flow_id, goal) if p.get("nodes") else None, "explanation": p.get("explanation", ""),
            "problems": problems}
