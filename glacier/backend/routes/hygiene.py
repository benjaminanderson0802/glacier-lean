"""Memory cleanup proposals. Applying changes always requires an explicit approval."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import memory_hygiene
import audit_log


router = APIRouter()


class HygieneDecision(BaseModel):
    approve: bool


@router.get("/api/memory/hygiene")
def list_hygiene_proposals():
    return memory_hygiene.list_proposals()


@router.post("/api/memory/hygiene/scan")
def scan_hygiene_proposals():
    result = memory_hygiene.scan()
    audit_log.record("memory.hygiene_scanned", what={"proposals": len(result) if isinstance(result, list) else None})
    return result


@router.post("/api/memory/hygiene/{proposal_id}")
def decide_hygiene_proposal(proposal_id: str, decision: HygieneDecision):
    try:
        result = memory_hygiene.decide(proposal_id, decision.approve)
        audit_log.record("memory.hygiene_applied" if decision.approve else "memory.hygiene_rejected",
                         what={"proposal_id": proposal_id, "approve": decision.approve})
        return result
    except FileNotFoundError:
        raise HTTPException(404, "memory proposal not found")
    except ValueError as exc:
        raise HTTPException(409, str(exc))
