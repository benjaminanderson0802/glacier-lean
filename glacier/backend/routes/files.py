"""Upload originals, manage projects, and create searchable document notes."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

import files_store
import audit_log
from bounded_body import read_bounded_body

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str
    model_config = ConfigDict(extra="forbid")


class UndoFileDelete(BaseModel):
    undo_id: str
    model_config = ConfigDict(extra="forbid")


async def _read_bounded_body(request: Request) -> None:
    await read_bounded_body(request, files_store.max_upload_bytes() + 64 * 1024,
                            files_store.too_large_message())


@router.post("/api/files")
async def upload_file(request: Request):
    await _read_bounded_body(request)
    form = await request.form()
    file = form.get("file")
    project = form.get("project")
    if not isinstance(file, UploadFile):
        await form.close()
        raise HTTPException(400, "Choose a file to upload")
    if project is not None and not isinstance(project, str):
        await form.close()
        raise HTTPException(400, "That project name is not allowed")
    try:
        filename = files_store.validate_filename(file.filename or "")
        if project:
            files_store.validate_project(project)
    except PermissionError as exc:
        await form.close()
        raise HTTPException(400, str(exc)) from exc
    except ValueError as exc:
        await form.close()
        raise HTTPException(400, str(exc)) from exc
    try:
        try:
            result = await run_in_threadpool(files_store.save_upload, filename, project, file.file)
            if not result.get("duplicate"):
                audit_log.record("file.uploaded", what={"path": result.get("path"), "project": result.get("project"),
                                                        "name": result.get("name"), "size": result.get("size")})
            return result
        except PermissionError as exc:
            raise HTTPException(400, str(exc)) from exc
        except ValueError as exc:
            status = 413 if "too large" in str(exc).lower() else 400
            raise HTTPException(status, str(exc)) from exc
    finally:
        await form.close()


@router.get("/api/files")
def list_files(project: str | None = None):
    try:
        return files_store.list_files(project)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.delete("/api/files")
def delete_file(project: str, name: str):
    try:
        return files_store.delete_file(project, name)
    except FileNotFoundError as exc:
        raise HTTPException(404, "Uploaded file not found") from exc
    except (PermissionError, ValueError) as exc:
        raise HTTPException(400, "That file name or project is not allowed") from exc


@router.post("/api/files/undo-delete")
def undo_delete_file(body: UndoFileDelete):
    try:
        return files_store.undo_delete_file(body.undo_id)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except FileExistsError as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/api/projects")
def list_projects():
    return files_store.list_projects()


@router.post("/api/projects")
def create_project(item: ProjectCreate):
    try:
        result = files_store.create_project(item.name)
        audit_log.record("project.created", what={"name": item.name})
        return result
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
