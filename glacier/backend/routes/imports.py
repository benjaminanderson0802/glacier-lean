"""HTTP endpoints for importing and refreshing local conversation exports."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

import import_service

router = APIRouter()


class ImportRequest(BaseModel):
    source: str
    path: str
    model_config = ConfigDict(extra="forbid")


def _error(exc: ValueError) -> HTTPException:
    return HTTPException(400, str(exc))


@router.post("/api/imports")
async def import_conversations(request: Request):
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        try:
            source = form.get("source")
            file = form.get("file")
            if not isinstance(source, str) or not isinstance(file, UploadFile):
                raise HTTPException(400, "Choose an export source and file")
            try:
                return await run_in_threadpool(import_service.import_export, source, upload=file.file,
                                               filename=file.filename or "export.zip")
            except ValueError as exc:
                raise _error(exc) from exc
        finally:
            await form.close()
    try:
        item = ImportRequest.model_validate(await request.json())
    except Exception as exc:
        raise HTTPException(400, "Choose ChatGPT or Claude and provide an export file path") from exc
    try:
        return await run_in_threadpool(import_service.import_export, item.source, item.path)
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/api/imports/refresh")
def refresh_imports():
    try:
        return import_service.refresh()
    except ValueError as exc:
        raise _error(exc) from exc


@router.get("/api/imports")
def list_imports():
    return import_service.list_imports()
