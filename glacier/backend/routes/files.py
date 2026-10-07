"""Upload originals, manage projects, and create searchable document notes."""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict

import files_store

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str
    model_config = ConfigDict(extra="forbid")


@router.post("/api/files")
async def upload_file(file: UploadFile = File(...), project: str | None = Form(default=None)):
    try:
        filename = files_store.validate_filename(file.filename or "")
        if project:
            files_store.validate_project(project)
    except PermissionError as exc:
        raise HTTPException(400, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    content = await file.read(files_store.max_upload_bytes() + 1)
    if len(content) > files_store.max_upload_bytes():
        raise HTTPException(413, "This file is too large. The upload limit is 50 MB by default.")
    try:
        return files_store.save_upload(filename, project, content)
    except PermissionError as exc:
        raise HTTPException(400, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/api/files")
def list_files(project: str | None = None):
    try:
        return files_store.list_files(project)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/api/projects")
def list_projects():
    return files_store.list_projects()


@router.post("/api/projects")
def create_project(item: ProjectCreate):
    try:
        return files_store.create_project(item.name)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
