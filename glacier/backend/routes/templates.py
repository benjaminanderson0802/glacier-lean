"""Bundled and community template API."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import template_registry
import re


router = APIRouter()


class TemplateImport(BaseModel):
    file: str


@router.get("/api/templates")
def list_templates():
    return template_registry.list_templates()


@router.post("/api/templates/import")
def import_template(body: TemplateImport):
    return template_registry.review_import(body.file)


@router.post("/api/templates/import/{proposal_id}/approve")
def approve_template(proposal_id: str):
    if not re.fullmatch(r"[0-9a-f]{32}", proposal_id):
        raise HTTPException(404, "Template proposal not found")
    try:
        return template_registry.approve_import(proposal_id)
    except FileNotFoundError:
        raise HTTPException(404, "Template proposal not found")
