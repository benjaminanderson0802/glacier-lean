"""Bundled and community template API."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import template_registry
import vault
import re


router = APIRouter()


class TemplateImport(BaseModel):
    file: str


class UndoTemplateDelete(BaseModel):
    undo_id: str
    model_config = {"extra": "forbid"}


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


@router.delete("/api/templates/{template_id}")
def delete_imported_template(template_id: str):
    try:
        undo_id = template_registry.delete_imported(template_id)
    except FileNotFoundError as exc:
        raise HTTPException(404, "Imported template not found") from exc
    vault.record_event("owner", "delete", {"kind": "imported_template", "id": template_id, "undo_id": undo_id})
    return {"deleted": True, "id": template_id, "undo_id": undo_id}


@router.post("/api/templates/undo-delete")
def undo_delete_template(body: UndoTemplateDelete):
    try:
        template_id = template_registry.undo_delete_imported(body.undo_id)
    except FileNotFoundError as exc:
        raise HTTPException(404, "Removed template not found") from exc
    except FileExistsError as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    vault.record_event("owner", "restore", {"kind": "imported_template", "id": template_id})
    return {"restored": True, "id": template_id}
