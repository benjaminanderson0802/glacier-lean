"""Offline first-run recommendations and creation of reviewed starter flows."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
from pathlib import Path

import system_check
import template_registry
import vault
import shell_commands
from app_paths import app_data_home


AGENTS = {
    "codex": ("Codex", "codex", ["--version"], "Apache-2.0", "https://github.com/openai/codex"),
    "opencode": ("OpenCode", "opencode", ["--version"], "MIT", "https://opencode.ai/docs/#install"),
    "gemini": ("Gemini CLI", "gemini", ["--version"], "Apache-2.0", "https://github.com/google-gemini/gemini-cli"),
    "claude": ("Claude Code", "claude", ["--version"], "Apache-2.0", "https://docs.anthropic.com/en/docs/claude-code/overview"),
}
_apply_lock = threading.Lock()

INSTALLS = {
    "ollama": ("Ollama", "MIT", "https://ollama.com/download", "Runs free models on this computer, so Glacier can work without an online model service."),
    "opencode": ("OpenCode", "MIT", "https://opencode.ai/docs/#install", "Lets Glacier hand coding tasks to a coding agent that is free and open source."),
    "codex-acp": ("Codex ACP adapter", "Apache-2.0", "https://github.com/agentclientprotocol/codex-acp#installation", "Connects an already installed Codex CLI to Glacier's coding-agent steps."),
    "gemini": ("Gemini CLI", "Apache-2.0", "https://github.com/google-gemini/gemini-cli", "Adds another open-source coding agent Glacier can use for coding tasks."),
    "claude": ("Claude Code", "Apache-2.0", "https://docs.anthropic.com/en/docs/claude-code/overview", "Adds a coding agent Glacier can use for coding tasks."),
}


def _version(command: str, args: list[str]) -> str:
    binary = shell_commands.which(command)
    if not binary:
        return ""
    try:
        result = subprocess.run([binary, *args], capture_output=True, text=True, timeout=2, check=False, shell=False)
    except (OSError, subprocess.SubprocessError):
        return ""
    if result.returncode:
        return ""
    return next((line.strip() for line in (result.stdout + "\n" + result.stderr).splitlines() if line.strip()), "")


def _agent_discovery() -> list[dict]:
    found = []
    for key, (name, command, args, _license, _url) in AGENTS.items():
        version = _version(command, args)
        found.append({"id": key, "name": name, "found": bool(version), "version": version,
                      "usable_as_step": key == "codex" and bool(version)})
    # ACP presets are currently only available for OpenCode and the Codex adapter.
    for name, command in (("OpenCode", "opencode"), ("Codex ACP", "codex-acp")):
        found.append({"id": "acp-" + command, "name": name, "found": bool(shell_commands.which(command)),
                      "version": _version(command, ["--version"]), "usable_as_step": bool(shell_commands.which(command))})
    return found


def _requirements(flow: dict, machine: dict, agents: list[dict]) -> tuple[bool, list[str]]:
    models = set(machine.get("ollama_models") or [])
    tools = machine.get("tools") or {}
    agent_map = {item["id"]: item["found"] for item in agents}
    missing = []
    for node in flow.get("nodes", []):
        kind, config = node.get("type"), node.get("config") or {}
        if kind == "local_ai":
            model = config.get("model") or (machine.get("recommended") or {}).get("local_model")
            if not (tools.get("ollama") or {}).get("found"):
                missing.append("Ollama")
            elif model not in models:
                missing.append(f"the {model} model")
        elif kind == "codex" and not agent_map.get("codex", False):
            missing.append("Codex")
        elif kind == "acp_agent":
            harness = config.get("harness") or "opencode"
            if harness in ("opencode", "codex-acp") and not agent_map.get("acp-" + harness, False):
                missing.append("OpenCode" if harness == "opencode" else "Codex ACP")
        elif kind == "command":
            command = str(config.get("cmd") or "")
            for tool, pattern in (("curl", r"\bcurl\b"), ("git", r"\bgit\b"), ("python", r"\bpython(?:3)?\b"), ("node", r"\bnode\b")):
                if re.search(pattern, command) and not (tools.get(tool) or {}).get("found"):
                    missing.append(tool)
    return not missing, sorted(set(missing))


def proposal() -> dict:
    machine = system_check.check_system()
    recommendation = machine.get("recommended") or system_check.recommend(machine)
    memory = machine.get("memory_gb")
    mode = recommendation["mode"]
    model = recommendation["local_model"]
    reason = (f"Your computer has {memory:g} GB of memory, so Glacier uses the light mode."
              if memory is not None and mode == "low" else
              "Your computer has enough memory for Glacier's standard mode." if mode == "standard" else
              "Your computer has limited processing power, so Glacier uses the light mode.")
    agents = _agent_discovery()
    installed = {item["id"] for item in agents if item["found"]}
    suggestions = []
    candidates = []
    for item in template_registry.list_templates():
        flow = item.get("template") or {}
        okay, absent = _requirements(flow, machine, agents)
        if not item.get("installable") or not okay:
            continue
        needs_model = any(node.get("type") == "local_ai" for node in flow.get("nodes", []))
        if not any(node.get("type") in {"codex", "acp_agent", "local_ai"} for node in flow.get("nodes", [])):
            continue
        candidates.append({"template_id": item["id"], "name": item["name"],
                           "why": "All tools and models this automation needs are available on your computer.",
                           "requires_local_model": needs_model})
    # Prefer useful AI automations that the machine can actually run; fill the remaining
    # slots with simple automations that need no AI or external service.
    suggestions = [entry for entry in candidates if entry["requires_local_model"] or
                   any(agent["usable_as_step"] and agent["found"] for agent in agents)][:3]
    if len(suggestions) < 3:
        selected = {entry["template_id"] for entry in suggestions}
        suggestions.extend([entry for entry in candidates if entry["template_id"] not in selected][:3 - len(suggestions)])
    missing_useful = []
    for key in ("opencode", "codex-acp", "ollama", "gemini", "claude"):
        name, license_name, url, why = INSTALLS[key]
        probe_key = "ollama" if key == "ollama" else "acp-codex-acp" if key == "codex-acp" else key
        if (machine.get("tools", {}).get("ollama", {}).get("found") if key == "ollama" else probe_key in installed):
            continue
        missing_useful.append({"name": name, "why": why, "license": license_name, "download_page": url})
        if len(missing_useful) == 3:
            break
    return {"applied": (_home() / "starter_templates.json").exists(), "mode": mode, "local_model": model, "reason": reason,
            "coding_agents_found": agents, "suggested_automations": suggestions,
            "missing_but_useful": missing_useful}


def _home() -> Path:
    return app_data_home()


def apply(template_ids: list[str], mode: str) -> dict:
    if mode not in {"low", "standard"}:
        raise ValueError("Choose either light or standard mode.")
    available = {item["id"]: item for item in template_registry.list_templates() if item.get("installable")}
    for template_id in template_ids:
        if template_id not in available:
            raise KeyError(template_id)
    templates = [available[template_id] for template_id in dict.fromkeys(template_ids)]
    with _apply_lock:
        root = _home()
        env_dir = root / "vault" / "environments"
        existing_ids = set()
        applied_path = root / "starter_templates.json"
        try:
            applied = set(json.loads(applied_path.read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError):
            applied = set()
        created = []
        for item in templates:
            if item["id"] in applied:
                continue
            existing_ids = {path.stem for path in env_dir.glob("*.json")}
            base = re.sub(r"[^a-z0-9]+", "-", item["name"].lower()).strip("-") or "automation"
            env_id, suffix = base, 2
            while env_id in existing_ids:
                env_id, suffix = f"{base}-{suffix}", suffix + 1
            existing_ids.add(env_id)
            flow = dict(item["template"])
            flow.update({"id": env_id, "name": item["name"]})
            # Match the gallery's environment validation and vault write path.
            import app as backend_app
            backend_app.validate_environment(env_id, flow)
            vault.write_note(f"environments/{env_id}.json", json.dumps(flow, indent=2), agent="glacier-api")
            applied.add(item["id"])
            created.append({"template_id": item["id"], "id": env_id, "name": item["name"]})
        old_settings = system_check.effective_settings()
        settings = {"mode": mode, "local_model": old_settings.get("local_model") or system_check.RECOMMENDED_MODELS[mode],
                    "max_parallel_runs": 1 if mode == "low" else old_settings.get("max_parallel_runs", 1)}
        (_home() / "settings.json").write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
        applied_path.write_text(json.dumps(sorted(applied), indent=2) + "\n", encoding="utf-8")
        return {"created": created, "mode": mode, "local_model": settings["local_model"]}
