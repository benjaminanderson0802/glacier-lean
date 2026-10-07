"""Upload originals, manage projects, and create searchable document notes."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from starlette.datastructures import UploadFile

import files_store

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str
    model_config = ConfigDict(extra="forbid")


async def _read_bounded_body(request: Request) -> None:
    limit = files_store.max_upload_bytes() + 64 * 1024
    try:
        declared = int(request.headers.get("content-length", "0"))
    except ValueError:
        declared = 0
    if declared > limit:
        raise HTTPException(413, files_store.too_large_message())

    chunks = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            raise HTTPException(413, files_store.too_large_message())
        chunks.append(chunk)
    request._body = b"".join(chunks)


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
            return files_store.save_upload(filename, project, file.file)
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


@router.get("/api/projects")
def list_projects():
    return files_store.list_projects()


@router.post("/api/projects")
def create_project(item: ProjectCreate):
    try:
        return files_store.create_project(item.name)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
