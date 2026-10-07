"""Claims API (docs/contracts/VERIFICATION.md)."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import claims, claims_research

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


@router.post("/api/claims/{cid}/decision")
def decide(cid: str, d: Decision):
    try:
        return claims.decide(cid, d.action, d.option)
    except FileNotFoundError:
        raise HTTPException(404, "claim not found")
    except ValueError as e:
        raise HTTPException(400, str(e))
