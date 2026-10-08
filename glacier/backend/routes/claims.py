"""Claims API (docs/contracts/VERIFICATION.md)."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import claims, claims_research, runner, store, vault

router = APIRouter()


class NewClaim(BaseModel):
    kind: str
    summary: str
    evidence: str = ""
    run_id: str = ""
    node_id: str = ""
    attempts_made: int = 0


class Decision(BaseModel):
    action: str
    option: str = ""


@router.post("/api/claims")
def file_claim(c: NewClaim):
    try:
        r = claims.file_claim(c.kind, c.summary, c.evidence, c.run_id, c.node_id, c.attempts_made, filed_by="owner")
    except ValueError as e:
        raise HTTPException(400, str(e))
    claims_research.start(r["id"])
    return r


@router.get("/api/claims")
def list_claims(status: str | None = None):
    return claims.list_claims(status)


@router.get("/api/claims/{cid}")
def get_claim(cid: str):
    try:
        return claims.get_claim(cid)
    except (ValueError, FileNotFoundError):
        raise HTTPException(404, "claim not found")


@router.delete("/api/claims/{cid}")
def delete_claim(cid: str):
    try:
        path = claims._path(cid)
        commit = vault.delete_note(path, agent="owner", kind="claim")
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(404, "claim not found") from exc
    store.broadcaster.publish({"type": "claim", "id": cid, "status": "deleted"})
    return {"deleted": True, "id": cid, "commit": commit}


class UndoDelete(BaseModel):
    commit: str


@router.post("/api/claims/{cid}/undo-delete")
def undo_delete_claim(cid: str, body: UndoDelete):
    try:
        path = claims._path(cid)
        commit = vault.restore_deleted_note(path, body.commit)
    except FileNotFoundError as exc:
        raise HTTPException(404, "claim not found") from exc
    except FileExistsError as exc:
        raise HTTPException(409, "That claim already exists") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    store.broadcaster.publish({"type": "claim", "id": cid, "status": "restored"})
    return {"restored": True, "commit": commit}


@router.post("/api/claims/{cid}/decision")
def decide(cid: str, d: Decision):
    try:
        return claims.decide(cid, d.action, d.option)
    except FileNotFoundError:
        raise HTTPException(404, "claim not found")
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/api/claims/{cid}/rerun")
def rerun_claim(cid: str):
    """After a decision, run the flow that raised the claim again so the owner sees whether it is fixed now."""
    try:
        c = claims.get_claim(cid)
    except (ValueError, FileNotFoundError):
        raise HTTPException(404, "claim not found")
    meta, body = c["meta"], c["body"]
    run = store.get_run(meta.get("run_id") or "") if meta.get("run_id") else None
    if not run:
        raise HTTPException(400, "This claim did not come from a run, so there is nothing to run again.")
    env_id = run["env_id"]
    try:
        def append_rerun(meta: dict, body: str):
            nonlocal run_id
            run_id = runner.start_run(env_id, {"_rerun_of": cid})
            meta.update(updated=claims._now())
            body = claims.append_resolution(body, f"- {claims._now()} Owner ran the flow again to check: run {run_id}.")
            return meta, body

        run_id = ""
        saved = claims.update_claim(cid, append_rerun, agent="owner")
    except FileNotFoundError:
        raise HTTPException(400, "The flow behind this claim no longer exists.")
    store.broadcaster.publish({"type": "claim", "id": cid, "status": saved["meta"].get("status")})
    return {"run_id": run_id, "env_id": env_id}
