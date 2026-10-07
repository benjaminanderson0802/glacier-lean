"""Memory cleanup proposals. Applying changes always requires an explicit approval."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import memory_hygiene


router = APIRouter()


class HygieneDecision(BaseModel):
    approve: bool


@router.get("/api/memory/hygiene")
def list_hygiene_proposals():
    return memory_hygiene.list_proposals()


@router.post("/api/memory/hygiene/scan")
def scan_hygiene_proposals():
    return memory_hygiene.scan()


@router.post("/api/memory/hygiene/{proposal_id}")
def decide_hygiene_proposal(proposal_id: str, decision: HygieneDecision):
    try:
        return memory_hygiene.decide(proposal_id, decision.approve)
    except FileNotFoundError:
        raise HTTPException(404, "memory proposal not found")
    except ValueError as exc:
        raise HTTPException(409, str(exc))
