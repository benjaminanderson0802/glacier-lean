"""Guided first-run setup."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import starter
import system_check
import audit_log

router = APIRouter()


class StarterApply(BaseModel):
    template_ids: list[str]
    mode: str


@router.get("/api/starter")
def get_starter():
    return starter.proposal()


@router.post("/api/starter/apply")
def apply_starter(body: StarterApply):
    try:
        result = starter.apply(body.template_ids, body.mode)
        system_check.clear_cache()
        audit_log.record("starter.applied", what={"mode": body.mode, "template_ids": body.template_ids,
                                                   "created": [item.get("id") for item in result.get("created", [])]})
        return result
    except KeyError:
        raise HTTPException(400, "We could not find the selected starter automation.")
    except ValueError as exc:
        raise HTTPException(400, str(exc))
