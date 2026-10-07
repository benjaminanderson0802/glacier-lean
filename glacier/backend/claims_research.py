"""Automatic claim research and routing (roadmap: claim research workflow, triage and routing to specialists).
Starts the moment a claim is filed; no human needed unless nothing free fits or the requirement is unclear.
  1. past fixes: resolved claims in memory that look like this one
  2. free/open-source research (capability gaps): a researcher worker (Codex, read-only) lists options with sources
  3. routing by kind: environment -> fixer, bug/skill_gap -> debugger, capability_gap -> fixer if a free option was
     found, else a proposal to the owner; unclear_spec/policy -> owner
Specialists then work the claim under the same verification rules (docs/contracts/VERIFICATION.md)."""
import os, re, subprocess, tempfile
from dbos import DBOS
import claims, vault, store

ROUTES = {"environment": "fixer", "bug": "debugger", "skill_gap": "debugger", "unclear_spec": "owner", "policy": "owner"}
RESEARCH_TIMEOUT = 15 * 60


def _research_prompt(meta: dict, body: str) -> str:
    return ("You are Glacier's researcher. Find FREE and OPEN-SOURCE ways to solve this problem. For each option give: name, "
            "license, link, how actively maintained, and how well it fits (percent). Prefer maintained, permissively licensed "
            "projects; never recommend paid or closed tools as the answer, but you may list them separately under 'Paid "
            "options' with price and lock-in.\n\nProblem: " + meta.get("summary", "") + "\n\n" + body[:4000] +
            "\n\nEnd with exactly one line: either 'VERDICT: FREE OPTION FOUND' or 'VERDICT: NO FREE OPTION FITS'.")


def run_researcher(prompt: str) -> str:
    """Read-only Codex run (sandbox default model). GLACIER_RESEARCH_BIN overrides the binary (tests)."""
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "out.txt")
        args = [os.environ.get("GLACIER_RESEARCH_BIN") or os.environ.get("CODEX_BIN", "codex"), "exec", "--json",
                "--skip-git-repo-check", "-s", "read-only", "-C", d, "-o", out, "--", prompt]
        try:
            p = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=RESEARCH_TIMEOUT)
        except (OSError, subprocess.TimeoutExpired) as e:
            return f"research could not run: {e}"
        if os.path.exists(out):
            with open(out) as f:
                return f.read().strip()
        return f"research failed (exit {p.returncode}): {(p.stdout + p.stderr)[-500:]}"


@DBOS.step()
def past_fixes(cid: str) -> list[str]:
    meta = claims.get_claim(cid)["meta"]
    words = re.findall(r"[a-zA-Z]{4,}", meta.get("summary", ""))
    hits = vault.search(" ".join(words[:8]), k=10) if words else []
    out = []
    for p in hits:
        if p.startswith("claims/") and p != f"claims/{cid}.md":
            try:
                m = claims.get_claim(p[len("claims/"):-3])["meta"]
            except Exception:
                continue
            if m.get("status") == "resolved":
                out.append(f"{p}: {m.get('summary')} -> {m.get('resolution')}")
    return out[:5]


@DBOS.step()
def research(cid: str) -> str:
    c = claims.get_claim(cid)
    return run_researcher(_research_prompt(c["meta"], c["body"]))


@DBOS.step(retries_allowed=True, max_attempts=3)
def record_and_route(cid: str, fixes: list, findings: str) -> dict:
    c = claims.get_claim(cid)
    meta, body = c["meta"], c["body"]
    kind = meta.get("kind")
    section = "## Research\n"
    section += ("Past fixes that look similar:\n" + "\n".join(f"- {f}" for f in fixes) + "\n\n") if fixes else "No similar past fix found.\n\n"
    if findings:
        section += "Free/open-source search:\n" + findings.strip() + "\n"
    if kind == "capability_gap":
        free = "VERDICT: FREE OPTION FOUND" in findings.upper()  # past similar claims are hints only; the verdict decides
        assigned, status = ("fixer", "routed") if free else ("owner", "proposed")
    else:
        assigned = ROUTES.get(kind, "researcher")
        status = "proposed" if assigned == "owner" else "routed"
    if status == "proposed":
        section += ("\n## Proposal\nNo free option fits (or this needs your decision). Options, costs, lock-in and the "
                    "recommendation are in the research above. Approve one option, reject (the task gets a workaround or is "
                    "deferred), or ask for more research.\n")
    body = re.sub(r"## Research\n.*?(?=\n## Resolution)", section.rstrip() + "\n", body, flags=re.S) if "## Research" in body else body + "\n" + section
    meta.update(status=status, assigned_to=assigned, updated=claims._now())
    vault.write_note(claims._path(cid), claims._render(meta, body), agent="glacier-researcher")
    store.broadcaster.publish({"type": "claim", "id": cid, "status": status})
    return {"status": status, "assigned_to": assigned, "has_run": bool(meta.get("run_id"))}


@DBOS.workflow()
def research_claim(cid: str) -> dict:
    fixes = past_fixes(cid)
    kind = claims.get_claim(cid)["meta"].get("kind")
    # capability gaps are always researched (a similar past claim is a hint, not a reason to skip the free-option search)
    findings = research(cid) if kind == "capability_gap" or (kind == "skill_gap" and not fixes) else ""
    r = record_and_route(cid, fixes, findings)
    if r.get("has_run") and r["status"] == "routed":
        import claims_specialist
        claims_specialist.maybe_start(cid, r["assigned_to"])  # specialists repair, then the flow is re-run as proof
    return r


def start(cid: str) -> None:
    """Called right after a claim is filed (API, MCP tool, or the runner's stuck signal)."""
    if os.environ.get("GLACIER_AUTO_RESEARCH", "1") == "1":
        DBOS.start_workflow(research_claim, cid)
