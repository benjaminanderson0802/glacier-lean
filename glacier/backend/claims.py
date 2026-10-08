"""Claims: every gap, blocker or missing capability becomes a plain markdown file in memory (rule I-15).
Format: docs/contracts/VERIFICATION.md. Files live at vault/claims/YYYY-MM-DD-<slug>.md, one git commit per change."""
import hashlib, json, re
from datetime import datetime, timezone
import vault, store

KINDS = ("bug", "environment", "capability_gap", "skill_gap", "unclear_spec", "policy")
STATUSES = ("filed", "researching", "resolved", "routed", "proposed", "closed")
FIELDS = ("id", "filed_by", "run_id", "node_id", "checkpoint", "kind", "summary", "attempts_made", "status",
          "assigned_to", "resolution", "resolution_evidence", "updated")


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _render(meta: dict, body: str) -> str:
    head = "\n".join(f"{k}: {json.dumps(meta.get(k, ''), ensure_ascii=False)}" for k in FIELDS)
    return f"---\n{head}\n---\n{body.strip()}\n"


def _parse(text: str) -> tuple[dict, str]:
    m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    if not m:
        raise ValueError("not a claim file")
    meta = {}
    for line in m.group(1).splitlines():
        k, _, v = line.partition(": ")
        try:
            meta[k] = json.loads(v)
        except ValueError:
            meta[k] = v
    return meta, m.group(2)


def _path(cid: str) -> str:
    if not re.fullmatch(r"[a-z0-9-]{8,80}", cid or ""):
        raise ValueError("unknown claim")
    return f"claims/{cid}.md"


def append_resolution(body: str, text: str) -> str:
    """Append text inside the claim's single Resolution section."""
    marker = "## Resolution"
    before, sep, resolution = body.partition(marker)
    if not sep:
        before = body.rstrip()
        resolution = ""
        sep = "\n\n" + marker
    # Older notes may already have duplicate Resolution headings. Keep the
    # first section and fold their contents into it before appending.
    resolution = re.sub(r"\n## Resolution\s*", "\n", resolution)
    return before.rstrip() + sep + resolution.rstrip() + "\n" + text.strip() + "\n"


def file_claim(kind: str, summary: str, evidence: str, run_id: str = "", node_id: str = "", attempts_made: int = 0,
               filed_by: str = "glacier", checkpoint: str = "") -> dict:
    if kind not in KINDS:
        raise ValueError(f"kind must be one of: {', '.join(KINDS)}")
    if not (summary or "").strip():
        raise ValueError("a claim needs a short summary of the problem")
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = re.sub(r"[^a-z0-9]+", "-", summary.lower()).strip("-")[:40] or "claim"
    cid = f"{day}-{slug}-{hashlib.sha256(f'{summary}{run_id}{node_id}{_now()}'.encode()).hexdigest()[:6]}"
    meta = {"id": cid, "filed_by": filed_by, "run_id": run_id or "", "node_id": node_id or "", "checkpoint": checkpoint,
            "kind": kind, "summary": summary.strip(), "attempts_made": int(attempts_made or 0), "status": "filed",
            "assigned_to": "researcher", "resolution": "", "resolution_evidence": "", "updated": _now()}
    body = f"## Problem\n{summary.strip()}\n\n## Evidence\n{(evidence or '').strip()}\n\n## Research\n\n## Resolution\n"
    path = _path(cid)
    with vault._lock:
        vault.write_note(path, _render(meta, body), agent=filed_by)
    store.broadcaster.publish({"type": "claim", "id": cid, "status": "filed"})
    return {"id": cid, "path": path}


def list_claims(status: str | None = None) -> list[dict]:
    out = []
    for p in vault.list_notes(".md", "claims"):
        try:
            meta, _ = _parse(vault.read_note(p))
        except (ValueError, FileNotFoundError):
            continue
        if status and meta.get("status") != status:
            continue
        out.append({k: meta.get(k) for k in ("id", "kind", "summary", "status", "assigned_to", "updated")})
    return sorted(out, key=lambda c: c.get("updated") or "", reverse=True)


def get_claim(cid: str) -> dict:
    meta, body = _parse(vault.read_note(_path(cid)))
    return {"meta": meta, "body": body}


def update_claim(cid: str, fn, *, agent: str = "glacier") -> dict:
    """Read, modify and save one claim atomically with respect to every claim writer."""
    with vault._lock:
        meta, body = _parse(vault.read_note(_path(cid)))
        result = fn(meta, body)
        if result is not None:
            meta, body = result
        vault.write_note(_path(cid), _render(meta, body), agent=agent)
        return {"meta": meta, "body": body}


def decide(cid: str, action: str, option: str = "", by: str = "owner") -> dict:
    """Owner decision on a claim (usually a proposal): approve | reject | research_more."""
    if action not in ("approve", "reject", "research_more"):
        raise ValueError("action must be approve, reject or research_more")
    status = {"approve": "resolved", "reject": "closed", "research_more": "researching"}[action]
    words = {"approve": f"Approved by the owner{': ' + option if option else ''}.", "reject": "Rejected by the owner.",
             "research_more": "Owner asked for more research."}[action]
    def apply(meta: dict, body: str):
        meta.update(status=status, updated=_now(), assigned_to="researcher" if action == "research_more" else meta.get("assigned_to"))
        if action != "research_more":
            meta["resolution"] = words
        body = body.rstrip() + f"\n- {_now()} {words}\n"
        return meta, body

    update_claim(cid, apply, agent=by)
    store.broadcaster.publish({"type": "claim", "id": cid, "status": status})
    return {"status": status}
