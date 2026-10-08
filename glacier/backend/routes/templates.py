"""Bundled and community template API."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import template_registry
import re
import audit_log


router = APIRouter()


class TemplateImport(BaseModel):
    file: str


@router.get("/api/templates")
def list_templates():
    return template_registry.list_templates()


@router.post("/api/templates/import")
def import_template(body: TemplateImport):
    result = template_registry.review_import(body.file)
    audit_log.record("template.reviewed", what={"proposal_id": result.get("id"), "accepted": result.get("accepted")})
    return result


@router.post("/api/templates/import/{proposal_id}/approve")
def approve_template(proposal_id: str):
    if not re.fullmatch(r"[0-9a-f]{32}", proposal_id):
        raise HTTPException(404, "Template proposal not found")
    try:
        result = template_registry.approve_import(proposal_id)
        audit_log.record("template.approved", what={"proposal_id": proposal_id, "env_id": result.get("id")})
        return result
    except FileNotFoundError:
        raise HTTPException(404, "Template proposal not found")
