"""Graph runner: each run is the DBOS workflow run_environment(env_id, run_id) (workflow id == run_id); each node
execution is a DBOS step, so after a crash finished nodes are replayed from DBOS's record instead of re-run."""
import json, os, re, uuid, operator, sqlite3, subprocess, tempfile, threading, time
import shlex
from collections import defaultdict, deque
from queue import Empty, Queue
from dbos import DBOS, SetWorkflowID
import store, vault, decider, plugins, verify, claims, workspaces, memory_context, secrets_store, sandboxing, system_check
import shell_commands
import audit_log
from agents_md import project_instructions_detail

MAX_EXECUTIONS = 500  # default step limit per run; an environment may set its own "max_steps"
MAX_FLOW_DEPTH = 5
MAX_LOOP_TIMES = 1000
MAX_RETRIES = 10
MAX_STEP_FAILURES = 3  # stuck signal: a step failing this often in one run stops and files a claim
APPROVAL_TIMEOUT = 7 * 24 * 3600
COMMAND_TIMEOUT = 3600
OUTPUT_LIMIT = 20000
CODEX_TIMEOUT = 30 * 60
PREV_LIMIT = 8000
CODEX_LOGIN_HINT = "Codex not signed in \u2014 run: codex login --device-auth"
RUN_WAITING_MESSAGE = "Waiting for another run to finish"
MAX_PARALLEL_RUNS = max(1, int(system_check.effective_settings().get("max_parallel_runs", 1)))
_execution_slots = threading.BoundedSemaphore(MAX_PARALLEL_RUNS)
# steps with an exit_code that check nodes branch on: see plugins.is_worker
OPS = {"==": operator.eq, "!=": operator.ne, "<=": operator.le, ">=": operator.ge, "<": operator.lt, ">": operator.gt}


def schedule_name(env_id: str) -> str:
    return f"glacier-env-{env_id}"


def check(expr: str, exit_code: int) -> bool:
    """Tiny safe evaluator: `exit_code <op> <int>` clauses joined by and/or. Nothing is eval()'d."""
    def clause(text):
        m = re.fullmatch(r"\s*exit_code\s*(==|!=|<=|>=|<|>)\s*(-?\d+)\s*", text)
        if not m:
            raise ValueError(f"unsupported check expression: {text.strip()!r}")
        return OPS[m[1]](exit_code, int(m[2]))
    return any(all(clause(a) for a in re.split(r"\band\b", o)) for o in re.split(r"\bor\b", expr))


def env_path(env_id: str) -> str:
    if not isinstance(env_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", env_id):
        raise ValueError("environment id must use letters, numbers, dots, underscores, or hyphens")
    return f"environments/{env_id}.json"


def load_env(env_id: str) -> dict:
    return json.loads(vault.read_note(env_path(env_id)))


def start_run(env_id: str, run_settings: dict | None = None, run_id: str | None = None) -> str:
    """Snapshot the saved graph into a new run and start its workflow. run_settings are underscore keys
    for this run only (e.g. who started it), never saved into the flow."""
    run_id = run_id or uuid.uuid4().hex[:12]
    graph = load_env(env_id)
    graph.update({k: v for k, v in (run_settings or {}).items() if k.startswith("_")})
    store.create_run(run_id, env_id, graph)
    with SetWorkflowID(run_id):
        DBOS.start_workflow(run_environment, env_id, run_id)
    trigger = (run_settings or {}).get("_trigger") or {}
    return run_id


def run_codex(env_id: str, run_id: str, nid: str, cfg: dict, prev_output: str, timeout: int = CODEX_TIMEOUT, ws: str = "",
              on_process=None) -> dict:
    """Hand the prompt to `codex exec` (ChatGPT sign-in, no API key). Streams a short live log into the node output
    every ~2s; the final output is "codex exit <code>" plus Codex's last message."""
    fill = lambda s: s.replace("{env}", env_id).replace("{run}", run_id).replace("{prev_output}", prev_output[-PREV_LIMIT:])
    prompt = fill(cfg.get("prompt") or "")
    if secrets_store.PLACEHOLDER.search(prompt):
        raise ValueError("Secrets can't be sent to an AI model. Use the secret in a command step instead.")
    if not prompt.strip():
        raise ValueError("codex node has no prompt")
    prompt += memory_context.block(prompt, cfg)
    # GLACIER_CODEX_SANDBOX supplies the default only when this step has no setting.
    sandbox = cfg.get("sandbox") if cfg.get("sandbox") is not None else os.environ.get("GLACIER_CODEX_SANDBOX", "workspace-write")
    if sandbox not in ("read-only", "workspace-write", "danger-full-access"):
        raise ValueError(f"unsupported sandbox {sandbox!r}")
    home = os.path.abspath(os.environ.get("GLACIER_HOME", "data"))
    workdir = cfg.get("workdir") or ws or os.path.join(home, "workspaces", env_id)
    os.makedirs(workdir, exist_ok=True)
    instructions_detail = project_instructions_detail(workdir)
    fd, last_file = tempfile.mkstemp(prefix="codex-last-", suffix=".txt"); os.close(fd)
    executable = os.environ.get("CODEX_BIN", "codex")
    args = shell_commands.executable_invocation(executable, "exec", "--json", "--skip-git-repo-check", "-s", sandbox,
            "-C", workdir, "-o", last_file) + (["-m", cfg["model"]] if cfg.get("model") else []) + ["--", prompt]
    try:
        process_options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
        p = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                             cwd=workdir, **process_options)
    except FileNotFoundError:
        os.unlink(last_file)
        raise RuntimeError(f"Codex CLI not found ({args[0]}); install it, then run: codex login --device-auth")
    if on_process:
        on_process(p)
    timer = threading.Timer(timeout, terminate_process, args=(p,)); timer.start()
    log, errs, agent_msg, started, tok = [], [], "", time.time(), {}
    flushed = started
    lines = Queue()
    def read_stdout():
        try:
            for output_line in p.stdout:
                lines.put(output_line)
        finally:
            lines.put(None)
    reader = threading.Thread(target=read_stdout, daemon=True)
    reader.start()
    try:
        while True:
            try:
                line = lines.get(timeout=max(0, 2 - (time.time() - flushed)))
            except Empty:
                store.set_node(run_id, env_id, nid, "running", "\n".join(log[-40:]))
                flushed = time.time()
                continue
            if line is None:
                break
            line = line.strip()
            try:
                ev = json.loads(line)
            except ValueError:
                ev = None
            if isinstance(ev, dict):
                item = ev.get("item") or ev.get("msg")
                item = item if isinstance(item, dict) else {}
                err = ev.get("error")
                kind = item.get("type") if str(ev.get("type", "")).startswith("item.") else ev.get("type") or item.get("type")
                text = str(item.get("text") or item.get("message") or (err.get("message") if isinstance(err, dict) else err)
                           or ev.get("message") or "")
                if isinstance(ev.get("usage"), dict):
                    tok = ev["usage"]
                if kind == "agent_message" and text:
                    agent_msg = text
                elif "error" in str(kind) or "failed" in str(kind):
                    errs.append(text)
                log.append(f"{kind}: {text[:200]}" if text else str(kind))
            elif line:
                errs.append(line); log.append(line[:200])
            if time.time() - flushed >= 2:
                store.set_node(run_id, env_id, nid, "running", "\n".join(log[-40:]))
                flushed = time.time()
        code = p.wait()
    finally:
        timer.cancel()
        with open(last_file) as f:
            last_msg = f.read().strip()
        os.unlink(last_file)
    if code != 0 and re.search(r"not (logged|signed) in|login|unauthori[sz]ed|\b401\b", "\n".join(errs), re.I):
        raise RuntimeError(CODEX_LOGIN_HINT)
    body = last_msg or agent_msg or "\n".join(log[-20:])
    if code != 0 and time.time() - started >= timeout:
        body += f"\n[timed out after {timeout}s]"
    out = f"codex exit {code}\n{body}"
    if instructions_detail:
        out += f"\n{instructions_detail}"
    usage = {"model": cfg.get("model") or "default (sandbox Codex setting)", "route": "codex/chatgpt-plan", "cost_usd": 0.0,
             "tokens_in": tok.get("input_tokens", 0), "tokens_out": tok.get("output_tokens", 0)}
    return {"state": "done" if code == 0 else "failed", "output": out[-OUTPUT_LIMIT:], "exit_code": code, "usage": usage}


def terminate_process(process) -> None:
    """Stop a worker and its child processes without removing its workspace."""
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
    else:
        import signal
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


# ---- steps -------------------------------------------------------------------------------

@DBOS.step(retries_allowed=True, max_attempts=5)
def snapshot_scheduled_run(env_id: str, run_id: str) -> bool:
    """Create the run for a schedule tick, unless the flow no longer has a schedule (a tick that was already
    queued when the owner removed the schedule must not start the flow)."""
    graph = load_env(env_id)
    if not any(n.get("type") == "schedule" for n in graph.get("nodes", [])):
        return False
    store.create_run(run_id, env_id, graph)
    return True


def run_command(cfg: dict, timeout: int, ws: str = "", sandbox: bool = False) -> dict:
    """Run a shell command in its own process group so a time limit stops it and everything it started."""
    import signal
    env = dict(os.environ, GLACIER_WORKSPACE=ws,
               GLACIER_HOME=os.path.abspath(os.environ.get("GLACIER_HOME", "data"))) if ws else None
    if ws:
        os.makedirs(ws, exist_ok=True)
    command = cfg["cmd"]
    if sandbox:
        if not ws:
            raise ValueError("the sandbox needs a work folder")
        if cfg.get("network") == "allow":
            raise ValueError("Network access is not available for sandboxed steps yet")
        if os.name == "nt":
            raise RuntimeError("The step sandbox needs Linux; this step can't run sandboxed on Windows")
        command = sandboxing.wrap(command, os.path.abspath(ws), [])
        env = None
    options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    shell = not sandbox
    warning = ""
    if not sandbox:
        command, shell, warning = shell_commands.command_invocation(command)
    cwd = ws if sandbox else cfg.get("cwd") or ws or None
    if os.name == "nt" and cwd and not sandbox:
        cwd = os.path.abspath(cwd)
    p = subprocess.Popen(command, shell=shell, cwd=cwd, env=env, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True, **options)
    try:
        out, _ = p.communicate(timeout=timeout)
        code = p.returncode
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            # Git Bash can leave child processes holding our pipe open. Kill the
            # whole process tree, then bound cleanup rather than waiting for EOF.
            try:
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)],
                               capture_output=True, timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                pass
            try:
                p.kill()
            except OSError:
                pass
            if p.stdout:
                try:
                    p.stdout.close()
                except OSError:
                    pass
            try:
                p.wait(timeout=0.2)
            except subprocess.TimeoutExpired:
                pass
            out = ""
        else:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if os.name != "nt":
            out, _ = p.communicate()
        code, out = -1, f"{out or ''}\n[timed out after {timeout}s]"
    return {"state": "done" if code == 0 else "failed", "output": (warning + (out or ""))[-OUTPUT_LIMIT:], "exit_code": code}


@DBOS.step(retries_allowed=True, max_attempts=3)
def send_failure_alert(env_id: str, run_id: str, alert_urls: list) -> str:
    """One plain-language alert per failed run, through Apprise (ntfy, email, Discord, desktop, webhooks...).
    Targets: GLACIER_ALERT_URLS (comma separated) plus the environment's own "alert_urls"."""
    urls = [u.strip() for u in os.environ.get("GLACIER_ALERT_URLS", "").split(",") if u.strip()] + list(alert_urls or [])
    if not urls:
        return "no alert targets"
    import apprise
    run = store.get_run(run_id)
    bad = [n for n, st in run["node_states"].items() if st == "failed"]
    detail = (run["outputs"].get(bad[0], "") if bad else "")[-500:]
    name = (store.graph_of(run_id).get("name") or env_id)
    ap = apprise.Apprise()
    for u in urls:
        ap.add(u)
    ok = ap.notify(title=f"Glacier: '{name}' ({env_id}) failed",
                   body=f"Run {run_id} stopped at step {', '.join(bad) or '?'}.\n\nLast output:\n{detail}")
    audit_log.record("notification.sent" if ok else "notification.failed",
                     what={"run_id": run_id, "targets": len(urls), "channel": "apprise"})
    return "sent" if ok else "alert failed"


def _run_node_impl(env_id: str, run_id: str, node: dict, last: dict | None, ws: str = "") -> dict:
    """Execute one non-approval node. Returns {"state", "output", "exit_code"?, "branch"?}."""
    nid, kind, cfg = node["id"], node["type"], node.get("config") or {}
    try:
        trigger = store.graph_of(run_id).get("_trigger") or {}
    except (TypeError, KeyError, sqlite3.OperationalError):
        # Direct runner unit calls may have no persisted run snapshot (no row, or no run table yet).
        trigger = {}
    if kind not in ("file_trigger", "webhook_trigger"):
        cfg = _expand_trigger_values(cfg, trigger)
    store.set_node(run_id, env_id, nid, "running")
    try:
        run_record = store.get_run(run_id) or {"author": "owner"}
    except sqlite3.OperationalError:
        # Direct runner calls can run before app startup has initialized the
        # run-state database; they still need the default audit identity.
        run_record = {"author": "owner"}
    res = {"state": "done", "output": ""}
    try:
        if kind in ("command", "codex"):
            execution_cfg = dict(cfg)
            try:
                field = "cmd" if kind == "command" else "prompt"
                if kind == "codex" and secrets_store.PLACEHOLDER.search(str(cfg.get(field) or "")):
                    raise ValueError("Secrets can't be sent to an AI model. Use the secret in a command step instead.")
                if kind == "command":
                    command = str(cfg.get(field) or "").replace("{run}", run_id)
                    execution_cfg[field] = secrets_store.resolve(command)
            except ValueError as exc:
                match = re.search(r"Unknown secret: (.+)$", str(exc))
                if not match:
                    raise
                raise ValueError(f"This step uses a secret named {match.group(1)} that isn't saved yet. Add it in Settings > Secrets.") from None
            retries = max(0, min(int(cfg.get("retries") or 0), MAX_RETRIES))
            default_timeout = COMMAND_TIMEOUT if kind == "command" else CODEX_TIMEOUT
            timeout = max(1, min(int(cfg.get("timeout") or default_timeout), 24 * 3600))
            for attempt in range(1, retries + 2):
                if kind == "command":
                    sandbox_setting = execution_cfg.get("sandbox", "off")
                    env_sandbox = os.environ.get("GLACIER_SANDBOX", "off")
                    try:
                        if env_sandbox not in ("on", "off"):
                            raise ValueError("GLACIER_SANDBOX must be 'on' or 'off'")
                        if sandbox_setting not in ("on", "off"):
                            raise ValueError("sandbox must be 'on' or 'off'")
                        sandbox_on = env_sandbox == "on" or sandbox_setting == "on"
                        res = run_command(execution_cfg, timeout, ws, sandbox_on)
                    except (RuntimeError, NotImplementedError, ValueError) as exc:
                        res = {"state": "failed", "output": str(exc), "exit_code": 1}
                else:
                    res = run_codex(env_id, run_id, nid, execution_cfg, (last or {}).get("output") or "", timeout, ws)
                res["output"] = secrets_store.redact(str(res.get("output") or ""))
                if retries:
                    res["output"] = f"[attempt {attempt} of {retries + 1}]\n{res['output']}"[-OUTPUT_LIMIT:]
                if res["exit_code"] == 0 or attempt > retries:
                    break
                store.set_node(run_id, env_id, nid, "running", res["output"] + "\n[retrying]")
                time.sleep(min(attempt, 10))
            audit_log.record("step.command_executed" if kind == "command" else "outbound.model_call",
                             who=run_record.get("author", "owner"),
                             what={"env_id": env_id, "run_id": run_id, "node_id": nid,
                                   "step_type": kind, "exit_code": res.get("exit_code")})
        elif kind == "check":
            if last is None:
                raise ValueError("check has no previous command/codex result")
            ok = check(cfg.get("expr", "exit_code == 0"), last["exit_code"])
            res = {"state": "done", "output": "yes" if ok else "no", "branch": "yes" if ok else "no"}
        elif kind == "decide":
            options = decider.parse_options(cfg.get("options"))
            prev = (last or {}).get("output") or ""
            question = (cfg.get("question") or "").replace("{env}", env_id).replace("{run}", run_id).replace("{prev_output}", prev[-PREV_LIMIT:])
            d = decider.decide(question, options, prev, cfg.get("engine") or "auto", cfg.get("model") or "")
            audit_log.record("outbound.model_call", who=store.get_run(run_id).get("author", "owner"),
                             what={"env_id": env_id, "run_id": run_id, "node_id": nid, "step_type": "decide",
                                   "route": d.get("engine", "unknown")})
            res = {"state": "done", "output": f"decided: {d['choice']} (by {d['engine']})", "branch": d["choice"].strip().lower()}
        elif kind == "note":
            run = store.get_run(run_id)
            summary = ", ".join(f"{k}: {v}" for k, v in run["node_states"].items() if v != "pending")
            prev = (last or {}).get("output") or ""
            today = time.strftime("%Y-%m-%d", time.gmtime())
            # {prev_output} is the previous step's output (same limit as other steps); {date} is today's UTC date.
            fill_path = lambda s: s.replace("{env}", env_id).replace("{run}", run_id).replace("{date}", today)
            fill = lambda s: fill_path(s).replace("{summary}", summary).replace("{prev_output}", prev[-PREV_LIMIT:])
            path = fill_path(cfg.get("path") or "runs/{env}-{run}.md")
            sha = vault.write_note(path, secrets_store.redact(fill(cfg.get("template") or "Run {run} of {env}: {summary}")),
                                   agent="glacier-runner", run_id=run_id)
            audit_log.record("vault.note_written", who=run_record.get("author", "owner"),
                             what={"path": path, "run_id": run_id, "node_id": nid, "commit": sha})
            res["output"] = f"{path} (commit {sha})"
        elif kind in plugins.NODES:
            home = os.path.abspath(os.environ.get("GLACIER_HOME", "data"))
            ctx = {"env_id": env_id, "run_id": run_id, "node_id": nid, "config": cfg, "prev": last, "home": home, "workspace": ws,
                   "memory": lambda task: memory_context.block(task, cfg),
                   "log": lambda text: store.set_node(run_id, env_id, nid, "running", secrets_store.redact(str(text)[-OUTPUT_LIMIT:])),
                   "trigger": trigger if kind in ("file_trigger", "webhook_trigger") else {}}
            res = plugins.NODES[kind]["run"](ctx)
            if res.get("state") not in ("done", "failed") or not isinstance(res.get("output", ""), str):
                raise ValueError(f"step plug-in {kind!r} returned an invalid result")
            if plugins.is_worker(kind) and not isinstance(res.get("exit_code"), int):
                res["exit_code"] = 0 if res["state"] == "done" else 1
            res["output"] = secrets_store.redact(res.get("output", "")[-OUTPUT_LIMIT:])
            event = {"http_request": "outbound.http_request", "fetch_page": "outbound.web_fetch",
                     "web_search": "outbound.web_search", "read_document": "outbound.document_fetch",
                     "acp_agent": "outbound.agent_call", "local_ai": "outbound.model_call"}.get(kind)
            if event:
                safe = {"env_id": env_id, "run_id": run_id, "node_id": nid, "step_type": kind}
                if kind == "http_request":
                    safe["destination"] = re.sub(r"(://[^:/@]+):[^/@]+@", r"\1@", str(cfg.get("url", "")))
                    safe["method"] = str(cfg.get("method", "GET"))
                elif kind in {"fetch_page", "read_document"}:
                    safe["destination"] = str(cfg.get("url") or cfg.get("source") or "")
                elif kind == "web_search":
                    safe["destination"] = str(cfg.get("search_server", ""))
                audit_log.record(event, who=run_record.get("author", "owner"), what=safe)
        elif kind != "schedule":
            raise ValueError(f"unknown node type {kind!r}")
    except Exception as e:  # a broken node fails itself, not the whole server
        res = {"state": "failed", "output": secrets_store.redact(f"error: {e}"), "error": True}
    if isinstance(res.get("usage"), dict):
        store.record_usage(run_id, nid, res["usage"])
    store.set_node(run_id, env_id, nid, res["state"], res["output"])
    return res


def _expand_trigger_values(value, trigger):
    """Replace trigger placeholders in step settings without changing the saved environment."""
    file_path = str(trigger.get("file") or "")
    if os.name == "nt":  # command steps use Git Bash, which expects /c/Users/... paths
        match = re.match(r"^([A-Za-z]):[\\/](.*)$", file_path)
        if match:
            file_path = "/" + match.group(1).lower() + "/" + match.group(2).replace("\\", "/")
    body = trigger.get("body")
    body_text = json.dumps(body, ensure_ascii=False, separators=(",", ":")) if body is not None else ""
    def expand(item, command_field=False):
        if isinstance(item, str):
            file_value, body_value = (shlex.quote(file_path), shlex.quote(body_text)) if command_field else (file_path, body_text)
            return item.replace("{trigger_file}", file_value).replace("{trigger_body}", body_value)
        if isinstance(item, list):
            return [expand(child, command_field) for child in item]
        if isinstance(item, dict):
            return {key: expand(child, command_field or key == "cmd") for key, child in item.items()}
        return item
    return expand(value)


@DBOS.step()
def run_node(env_id: str, run_id: str, node: dict, last: dict | None, ws: str = "") -> dict:
    """Run one step while respecting the hardware-derived execution limit."""
    acquired = _execution_slots.acquire(blocking=False)
    if not acquired:
        store.set_run(run_id, "queued", RUN_WAITING_MESSAGE)
        store.set_node(run_id, env_id, node["id"], "queued", RUN_WAITING_MESSAGE)
        _execution_slots.acquire()
    try:
        store.set_run(run_id, "running")
        return _run_node_impl(env_id, run_id, node, last, ws)
    finally:
        _execution_slots.release()


@DBOS.step(retries_allowed=True, max_attempts=5)
def mark_waiting(env_id: str, run_id: str, node_id: str) -> None:
    # Persist both sides of the gate before publishing the node event, so API
    # readers cannot observe a waiting node while the run still looks running.
    store.set_waiting(run_id, env_id, node_id)


@DBOS.step(retries_allowed=True, max_attempts=5)
def finish_approval(env_id: str, run_id: str, node_id: str, msg: dict | None) -> dict:
    store.set_run(run_id, "running")
    if msg is None:
        res = {"state": "failed", "output": "timed out waiting for approval", "error": True}
    else:
        approved = bool(msg.get("approved"))
        res = {"state": "done", "output": "approved" if approved else "rejected", "branch": "yes" if approved else "no"}
    store.set_node(run_id, env_id, node_id, res["state"], res["output"])
    return res


@DBOS.step(retries_allowed=True, max_attempts=3)
def prepare_workspace(env_id: str, run_id: str, isolate: bool) -> str:
    return workspaces.prepare(os.path.abspath(os.environ.get("GLACIER_HOME", "data")), env_id, run_id, isolate)


@DBOS.step()
def finish_workspace(env_id: str, run_id: str, verified: bool) -> dict:
    r = workspaces.finish(os.path.abspath(os.environ.get("GLACIER_HOME", "data")), env_id, run_id, verified)
    store.record_workspace(run_id, r)
    return r


@DBOS.step()
def run_acceptance_check(env_id: str, run_id: str, idx: int, check: dict, last_output: str, ws: str = "") -> dict:
    """Runs one acceptance check outside the worker's control (rule I-04) and records the evidence."""
    home = os.path.abspath(os.environ.get("GLACIER_HOME", "data"))
    try:
        r = verify.run_check(home, env_id, check, last_output, ws)
    except Exception as e:
        r = {"passed": False, "evidence": f"the check could not run: {e}"}
    store.record_check(run_id, idx, check["kind"], r["passed"], r["evidence"])
    return r


@DBOS.step(retries_allowed=True, max_attempts=5)
def finish_human_check(env_id: str, run_id: str, idx: int, msg: dict | None) -> dict:
    store.set_run(run_id, "running")
    passed = bool(msg and msg.get("approved"))
    ev = "timed out waiting for the owner" if msg is None else ("approved by the owner" if passed else "rejected by the owner")
    store.record_check(run_id, idx, "human", passed, ev)
    return {"passed": passed, "evidence": ev}


@DBOS.step(retries_allowed=True, max_attempts=3)
def file_stuck_claim(env_id: str, run_id: str, node_id: str, attempts: int, output: str, rerun_of: str = "") -> str:
    """Stuck signal (same failure twice, or too many failures): stop repairing and file a claim (rules I-11, I-15).
    A proof re-run for an existing claim reports back to that claim instead of filing a new one."""
    if rerun_of:
        store.set_node(run_id, env_id, node_id, "failed", output[-OUTPUT_LIMIT:] + f"\n[stopped: still stuck after {attempts} attempts; reported to claim {rerun_of}]")
        return rerun_of
    c = claims.file_claim("bug", f"Step {node_id} in flow {env_id} keeps failing the same way",
                          f"Run {run_id}, step {node_id}, {attempts} failed attempts. Last output:\n\n{output[-2000:]}",
                          run_id=run_id, node_id=node_id, attempts_made=attempts, filed_by="glacier-runner")
    store.set_node(run_id, env_id, node_id, "failed", output[-OUTPUT_LIMIT:] + f"\n[stopped: stuck after {attempts} attempts; claim {c['id']} filed]")
    return c["id"]


@DBOS.step(retries_allowed=True, max_attempts=5)
def finish_run(env_id: str, run_id: str, status: str) -> None:
    store.skip_pending(run_id, env_id)
    store.set_run(run_id, status)
    graph = store.graph_of(run_id)
    conversation_id = graph.get("_assistant_conversation_id")
    if conversation_id and status in {"done", "failed", "rejected"} and store.mark_chat_reported(run_id):
        try:
            import run_explain
            import secrets_store
            import vault
            explanation = run_explain.explain_run(run_id)
            if explanation and explanation.get("summary"):
                path = f"conversations/{conversation_id}.md"
                previous = vault.read_note(path).rstrip()
                line = secrets_store.redact(explanation["summary"])
                stamp = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
                vault.write_note(path, previous + f"\n\n## {stamp}\n\n**Assistant:** {line}\n", agent="assistant")
        except Exception:
            # The durable run is already complete; a chat-note write must not fail or retry the workflow.
            import logging
            logging.getLogger(__name__).exception("Could not append run result to assistant conversation")


@DBOS.step(retries_allowed=True, max_attempts=5)
def loop_tick(env_id: str, run_id: str, node_id: str, count: int, times: int) -> dict:
    if count <= times:
        res = {"state": "running", "output": f"iteration {count} of {times}", "branch": "again"}
    else:
        res = {"state": "done", "output": f"finished {times} of {times}", "branch": "done"}
    store.set_node(run_id, env_id, node_id, res["state"], res["output"])
    return res


@DBOS.step(retries_allowed=True, max_attempts=5)
def start_child(env_id: str, run_id: str, node_id: str, child_env: str, child_run: str, depth: int) -> dict:
    """Snapshot the sub-flow's saved graph into its own run (visible in history like any run)."""
    try:
        if depth >= MAX_FLOW_DEPTH:
            raise ValueError(f"sub-flows nested more than {MAX_FLOW_DEPTH} deep; stopping")
        store.create_run(child_run, child_env, load_env(child_env))
        audit_log.record("run.child_started", who=store.get_run(run_id).get("author", "owner"),
                         what={"env_id": child_env, "run_id": child_run, "parent_run_id": run_id, "node_id": node_id})
        audit_log.record("run.child_started", who=store.get_run(run_id).get("author", "owner"),
                         what={"env_id": child_env, "run_id": child_run, "parent_run_id": run_id, "node_id": node_id})
    except (FileNotFoundError, ValueError) as e:
        msg = str(e) if "nested" in str(e) else f"sub-flow {child_env!r} not found"
        store.set_node(run_id, env_id, node_id, "failed", f"error: {msg}")
        return {"state": "failed", "output": f"error: {msg}", "error": True}
    store.set_node(run_id, env_id, node_id, "running", f"sub-run {child_run} of {child_env}")
    return {"state": "running"}


@DBOS.step(retries_allowed=True, max_attempts=5)
def finish_child(env_id: str, run_id: str, node_id: str, child_env: str, child_run: str, status: str) -> dict:
    code = 0 if status == "done" else 1
    res = {"state": "done" if code == 0 else "failed", "output": f"sub-run {child_run} of {child_env}: {status}", "exit_code": code}
    store.set_node(run_id, env_id, node_id, res["state"], res["output"])
    return res


# ---- workflows ---------------------------------------------------------------------------

@DBOS.workflow()
def run_environment(env_id: str, run_id: str, depth: int = 0) -> str:
    graph = store.graph_of(run_id)  # immutable snapshot taken when the run was created
    nodes = {n["id"]: n for n in graph["nodes"]}
    out = defaultdict(list)
    for e in graph.get("edges", []):
        if e["source"] in nodes and e["target"] in nodes:
            out[e["source"]].append(e)
    targets = {e["target"] for es in out.values() for e in es}
    trigger_node = (graph.get("_trigger") or {}).get("node_id")
    queue = deque([trigger_node] if trigger_node in nodes else
                  ([n for n in nodes if n not in targets] or list(nodes)[:1]))
    last, status, executions = ({"output": graph.get("_a2a_input", ""), "exit_code": 0}
                                if graph.get("_author") == "a2a" else None), "done", 0
    limit = int(graph.get("max_steps") or MAX_EXECUTIONS)
    loop_counts, flow_visits, failures = defaultdict(int), defaultdict(int), defaultdict(list)
    isolate = bool(graph.get("isolate"))
    ws = prepare_workspace(env_id, run_id, isolate)
    while queue:
        if executions >= limit:
            status = "failed"
            break
        executions += 1
        node = nodes[queue.popleft()]
        nid = node["id"]
        cfg = node.get("config") or {}
        if node["type"] == "approval":
            mark_waiting(env_id, run_id, nid)
            res = finish_approval(env_id, run_id, nid, DBOS.recv(topic=nid, timeout_seconds=APPROVAL_TIMEOUT))
        elif node["type"] == "loop":
            times = max(0, min(int(cfg.get("times") or 1), MAX_LOOP_TIMES))
            loop_counts[nid] += 1
            res = loop_tick(env_id, run_id, nid, loop_counts[nid], times)
            if res["branch"] == "done":
                loop_counts[nid] = 0  # an outer loop can run this loop again
        elif node["type"] == "flow":
            child_env = str(cfg.get("env") or "")
            flow_visits[nid] += 1
            child_run = uuid.uuid5(uuid.NAMESPACE_URL, f"{run_id}/{nid}/{flow_visits[nid]}").hex[:12]
            res = start_child(env_id, run_id, nid, child_env, child_run, depth)
            if not res.get("error"):
                with SetWorkflowID(child_run):
                    handle = DBOS.start_workflow(run_environment, child_env, child_run, depth + 1)
                res = finish_child(env_id, run_id, nid, child_env, child_run, handle.get_result())
        else:
            if node["type"] == "command" and cfg.get("sandbox") is None and graph.get("sandbox") is not None:
                node = dict(node, config=dict(cfg, sandbox=graph["sandbox"]))
            res = run_node(env_id, run_id, node, last, ws)
        edges = out[nid]
        if res.get("error"):
            status = "failed"
            break
        if plugins.is_worker(node["type"]):
            last = res
            if res["exit_code"] != 0:
                failures[nid].append(res.get("output", "")[-500:])
                f = failures[nid]
                if (len(f) >= 2 and f[-1] == f[-2]) or len(f) >= MAX_STEP_FAILURES:
                    cid = file_stuck_claim(env_id, run_id, nid, len(f), res.get("output", ""), graph.get("_rerun_of", ""))
                    if not graph.get("_rerun_of"):  # a re-run made to prove a fix never starts another repair cycle
                        import claims_research
                        claims_research.start(cid)
                    status = "failed"
                    break
            if res["exit_code"] != 0 and not any(nodes[e["target"]]["type"] == "check" for e in edges):
                status = "failed"  # a failing command only continues when a check handles it
                break
        if "branch" in res:
            edges = [e for e in edges if (e.get("label") or "").strip().lower() == res["branch"]]
            if not edges and node["type"] == "approval" and res["branch"] == "no":
                status = "rejected"
        queue.extend(e["target"] for e in edges)
    acceptance = graph.get("acceptance") or []
    if status == "done" and acceptance:  # done only when every required check passes (P-VERIFY)
        last_output = (last or {}).get("output") or ""
        for i, check in enumerate(acceptance):
            if check.get("kind") == "human":
                mark_waiting(env_id, run_id, f"check-{i}")
                r = finish_human_check(env_id, run_id, i, DBOS.recv(topic=f"check-{i}", timeout_seconds=APPROVAL_TIMEOUT))
            else:
                r = run_acceptance_check(env_id, run_id, i, check, last_output, ws)
            if not r["passed"] and check.get("required", True):
                # The owner saying no is a decision, not a broken run: report it as rejected and stop checking.
                if check.get("kind") == "human" and r.get("evidence") == "rejected by the owner":
                    status = "rejected"
                    break
                status = "failed"
    if isolate:
        finish_workspace(env_id, run_id, status == "done")
    finish_run(env_id, run_id, status)
    if status == "failed" and depth == 0:  # sub-flow failures are reported once, by the top-level run
        send_failure_alert(env_id, run_id, graph.get("alert_urls") or [])
    return status


@DBOS.workflow()
def scheduled_run(when, env_id) -> str:
    """Fired by the environment's DBOS schedule; starts a normal run (id derived from this workflow, so replay-safe)."""
    run_id = uuid.uuid5(uuid.NAMESPACE_URL, DBOS.workflow_id).hex[:12]
    if not snapshot_scheduled_run(env_id, run_id):
        return ""
    with SetWorkflowID(run_id):
        DBOS.start_workflow(run_environment, env_id, run_id)
    return run_id


def sync_schedule(env: dict) -> None:
    """Create/replace the environment's DBOS schedule from its schedule node, or delete it if there is none."""
    DBOS.delete_schedule(schedule_name(env["id"]))
    for n in env.get("nodes", []):
        if n["type"] == "schedule":
            DBOS.create_schedule(schedule_name=schedule_name(env["id"]), workflow_fn=scheduled_run,
                                 schedule=(n.get("config") or {}).get("cron", ""), context=env["id"])
            return
